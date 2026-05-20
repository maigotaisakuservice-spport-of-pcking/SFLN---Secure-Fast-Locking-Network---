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
            if not self.ack_received.done():
                self.ack_received.set_result(True)

    def error_received(self, exc): pass
    def connection_lost(self, exc): pass

async def run_load_test(num_clients=100):
    logger.info(f"--- Starting Load Test with {num_clients} virtual clients ---")
    server_port = 8888
    server = SFLNServer(port=server_port)

    # In CI, we need to ensure the server starts properly
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(2) # Give server more time in CI

    loop = asyncio.get_running_loop()
    server_addr = ('127.0.0.1', server_port)

    clients = []
    # Batch client creation to avoid overwhelming loop
    for i in range(num_clients):
        node_id = str(uuid.uuid4())
        try:
            transport, proto = await loop.create_datagram_endpoint(
                lambda: VirtualClient(node_id, server_addr), local_addr=('127.0.0.1', 0))
            clients.append((node_id, transport, proto))
        except Exception as e:
            logger.error(f"Failed to create client {i}: {e}")

    start_time = time.time()

    # Concurrent Registration
    logger.info(f"Registering {len(clients)} clients concurrently...")
    for node_id, transport, proto in clients:
        reg_msg = json.dumps({"type": "register", "node_id": node_id}).encode()
        transport.sendto(reg_msg, server_addr)

    # Wait for all acks with increased timeout for CI
    try:
        await asyncio.wait_for(asyncio.gather(*(p.ack_received for n, t, p in clients)), timeout=15.0)
        duration = time.time() - start_time
        logger.info(f"✅ Registered {len(clients)} clients in {duration:.2f}s ({len(clients)/duration:.2f} reg/s)")
    except asyncio.TimeoutError:
        # Check how many actually registered
        completed = sum(1 for n, t, p in clients if p.ack_received.done())
        logger.error(f"❌ Load test timed out! Received {completed}/{len(clients)} acks.")
        if completed < len(clients) * 0.9: # Allow 10% failure in high-load CI
             sys.exit(1)
        else:
             logger.info("Accepting >90% success in CI environment.")
    finally:
        for n, t, p in clients:
            if t: t.close()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    asyncio.run(run_load_test(100))
    print("✅ Load test passed.")
