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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Load-Test")

class VirtualClient:
    def __init__(self, node_id, server_addr):
        self.node_id = node_id
        self.server_addr = server_addr
        self.transport = None
        self.ack_received = asyncio.Future()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if b"reg_ack" in data:
            self.ack_received.set_result(True)

    def error_received(self, exc): pass
    def connection_lost(self, exc): pass

async def run_load_test(num_clients=100):
    logger.info(f"--- Starting Load Test with {num_clients} virtual clients ---")
    server_port = 8888
    server = SFLNServer(port=server_port)
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(1)

    loop = asyncio.get_running_loop()
    server_addr = ('127.0.0.1', server_port)

    clients = []
    for _ in range(num_clients):
        node_id = str(uuid.uuid4())
        transport, proto = await loop.create_datagram_endpoint(
            lambda: VirtualClient(node_id, server_addr), local_addr=('127.0.0.1', 0))
        clients.append((node_id, transport, proto))

    start_time = time.time()

    # Concurrent Registration
    logger.info(f"Registering {num_clients} clients concurrently...")
    for node_id, transport, proto in clients:
        transport.sendto(json.dumps({"type": "register", "node_id": node_id}).encode(), server_addr)

    # Wait for all acks with timeout
    try:
        await asyncio.wait_for(asyncio.gather(*(p.ack_received for n, t, p in clients)), timeout=10.0)
        duration = time.time() - start_time
        logger.info(f"✅ Registered {num_clients} clients in {duration:.2f}s ({num_clients/duration:.2f} reg/s)")
    except asyncio.TimeoutError:
        logger.error("❌ Load test timed out! Not all acks received.")
        sys.exit(1)
    finally:
        for n, t, p in clients:
            t.close()
        server_task.cancel()

if __name__ == "__main__":
    asyncio.run(run_load_test(100))
    print("✅ Load test passed.")
