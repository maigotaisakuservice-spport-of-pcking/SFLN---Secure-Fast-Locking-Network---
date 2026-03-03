import asyncio
import os
import sys
import uuid
import time
import logging
import json

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sfln.server.main import SFLNServer
from sfln.core import SFLNEngine
from sfln.core.crypto import SFLNCrypto

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("Integration-Test")

class AsyncUDPClient:
    def __init__(self):
        self.transport = None
        self.protocol = None
        self.queue = asyncio.Queue()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.queue.put_nowait((data, addr))

    def error_received(self, exc):
        logger.error(f"UDP Error: {exc}")

    def connection_lost(self, exc):
        pass

async def run_integration_test():
    server_port = 9998 # Use different port to avoid conflicts
    server = SFLNServer(port=server_port, log_level=logging.DEBUG)

    logger.info("Starting Relay Server...")
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(1)

    loop = asyncio.get_running_loop()
    server_addr = ('127.0.0.1', server_port)

    # Setup Async Clients
    transport_a, proto_a = await loop.create_datagram_endpoint(
        AsyncUDPClient, local_addr=('127.0.0.1', 0))
    transport_b, proto_b = await loop.create_datagram_endpoint(
        AsyncUDPClient, local_addr=('127.0.0.1', 0))

    client_a_id = str(uuid.uuid4())
    client_b_id = str(uuid.uuid4())

    # Shared master key for testing
    master_key = SFLNCrypto.generate_master_key()
    engine_a = SFLNEngine(node_id=client_a_id, master_key=master_key)
    engine_b = SFLNEngine(node_id=client_b_id, master_key=master_key)
    engine_a.backbone_addr = server_addr
    engine_b.backbone_addr = server_addr

    try:
        # 1. Register
        logger.info("Registering...")
        transport_a.sendto(json.dumps({"type": "register", "node_id": client_a_id}).encode(), server_addr)
        transport_b.sendto(json.dumps({"type": "register", "node_id": client_b_id}).encode(), server_addr)

        await asyncio.wait_for(proto_a.queue.get(), 2.0)
        await asyncio.wait_for(proto_b.queue.get(), 2.0)
        logger.info("Registration acks received.")

        # 2. Secure Send
        logger.info("Sending secure relayed data via manually constructed packet...")
        test_payload = b"Hello through Relay!"
        target_id_bytes = uuid.UUID(client_b_id).bytes

        # In current protocol:
        # Client to Server (UDP): [Magic(1)][Type(1)][TargetID(16)][Payload]
        # Type 0x01 is Relay.

        encrypted_chunks = engine_a.crypto.encrypt_data(test_payload)
        # Note: Server/main.py expects [Magic(1)][Type(1)][TargetID(16)][Payload]
        packet = bytearray([0x53, 0x01]) + target_id_bytes + encrypted_chunks[0]

        transport_a.sendto(packet, server_addr)

        # 3. Receive
        logger.info("Waiting for relayed packet...")
        data, addr = await asyncio.wait_for(proto_b.queue.get(), 2.0)
        logger.info(f"Received {len(data)} bytes from {addr}")

        # Server to Client (UDP): [Magic(1)][Type(1)][SourceID(16)][Payload]
        # Type 0x02 is Relayed.
        if data[0] == 0x53 and data[1] == 0x02:
            # Current Server implementation: relay_packet = bytearray([0x53, 0x02]) + source_id_bytes + data[18:]
            # But in UDP datagram_received: relay_packet = bytearray([0x53, 0x02]) + b'\x00'*16 + data[18:]
            # And data[18:] would be the chunk if TargetID was 16 bytes.

            # Wait, let's check server/main.py:
            # if data[0] == 0x53 and data[1] == 0x01:
            #     target_id = data[2:18]
            #     relay_packet = bytearray([0x53, 0x02]) + b'\x00'*16 + data[18:]

            decrypted = engine_b.crypto.decrypt_chunks([data[18:]])
            logger.info(f"Decrypted: {decrypted.decode()}")
            assert decrypted == test_payload
            logger.info("✅ INTEGRATION TEST SUCCESS!")
        else:
            logger.error(f"Wrong packet: {data.hex()}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Integration Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        transport_a.close()
        transport_b.close()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    asyncio.run(run_integration_test())
