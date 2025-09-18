import asyncio
import json
import argparse
import logging
import socket
import random
import sys
import os
import time
from collections import defaultdict
from routing import calculate_shortest_path

# --- Configuration ---
HOST = '127.0.0.1'
PORT_RANGE = range(9000, 9011)
UPDATE_INTERVAL_S = 7
SCAN_INTERVAL_S = 10

class Device:
    def __init__(self, name, port, test_unsafe_after=0):
        self.name = name
        self.port = port
        self.host = HOST
        self.server = None
        self.peers = {}  # name -> writer
        self.unsafe = False
        self.shutdown_event = asyncio.Event()
        self.test_unsafe_after = test_unsafe_after
        self.background_tasks = set() # CRITICAL FIX: Initialize the attribute

        self.topology = {self.name: {}}
        self.sequence_numbers = defaultdict(int)
        self.routing_table = {}

        self.logger = self._setup_logger()
        self.logger.info(f"Initializing on {self.host}:{self.port}")
        if self.test_unsafe_after > 0:
            self.logger.info(f"TEST MODE: Will mark as unsafe after {self.test_unsafe_after} seconds.")

    def _setup_logger(self):
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)
        if logger.hasHandlers(): logger.handlers.clear()

        log_dir = "sfln_p2p_project"
        os.makedirs(log_dir, exist_ok=True)
        handler = logging.FileHandler(f"{log_dir}/device-{self.name}.log", mode='w')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    async def _cleanup_peer(self, peer_name, writer):
        if peer_name and peer_name in self.peers and self.peers.get(peer_name) == writer:
            del self.peers[peer_name]
            self.logger.info(f"Peer '{peer_name}' removed. Current peers: {list(self.peers.keys())}")

            self.topology[self.name].pop(peer_name, None)
            if self.topology.get(peer_name): self.topology.pop(peer_name, None)
            for node in self.topology:
                if peer_name in self.topology[node]:
                    del self.topology[node][peer_name]

            await self.update_and_broadcast_lsa(force=True)

        if writer and not writer.is_closing():
            try: writer.close(); await writer.wait_closed()
            except Exception: pass

    async def _handle_connection(self, reader, writer):
        peer_name = None
        try:
            writer.write((json.dumps({"type": "hello", "name": self.name, "port": self.port}) + "\n").encode())
            await writer.drain()

            data = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if not data: return

            message = json.loads(data.decode().strip())
            peer_name = message.get('name')
            peer_port = message.get('port')

            if not peer_name or message.get('type') != 'hello' or peer_name == self.name: return

            if self.name > peer_name:
                self.logger.info(f"Tie-break: My name > '{peer_name}'. Dropping incoming connection.")
                return

            if peer_name in self.peers:
                self.logger.warning(f"Already connected to '{peer_name}'. Ignoring new connection.")
                return

            self.peers[peer_name] = writer
            self.logger.info(f"Connection with '{peer_name}' established. Peers: {list(self.peers.keys())}")
            await self.update_and_broadcast_lsa(force=True)
            await self.message_loop(reader, writer, peer_name)
        except Exception as e:
            self.logger.warning(f"Handshake/session failed with {peer_name or 'unknown'}: {e}")
        finally:
            await self._cleanup_peer(peer_name, writer)

    async def connect_to_peer(self, peer_host, peer_port):
        if self.unsafe or peer_port == self.port or any(w.get_extra_info('peername', (None, None))[1] == peer_port for w in self.peers.values() if not w.is_closing()): return
        if self.name < f"Device-at-port-{peer_port}": # Simplified name compare for tie-break
            try:
                reader, writer = await asyncio.wait_for(asyncio.open_connection(peer_host, peer_port), timeout=2.0)
                asyncio.create_task(self._handle_connection(reader, writer))
            except Exception: pass

    async def message_loop(self, reader, writer, peer_name):
        while not self.unsafe and peer_name in self.peers:
            try:
                line = await reader.readuntil(b'\n')
                if not line: break
                await self.handle_message(json.loads(line.decode().strip()), peer_name)
            except (asyncio.IncompleteReadError, ConnectionResetError): break
            except Exception as e: self.logger.error(f"Msg loop error with '{peer_name}': {e}"); break
        self.logger.info(f"Message loop for '{peer_name}' ended.")

    async def handle_message(self, msg, sender_name):
        # ... (same as previous version)
        msg_type = msg.get("type")
        if msg_type == "lsa":
            origin, seq, links = msg.get("origin"), msg.get("seq"), msg.get("links", {})
            if origin != self.name and seq > self.sequence_numbers[origin]:
                self.logger.info(f"Received new LSA from '{origin}' (seq={seq})")
                self.sequence_numbers[origin] = seq
                self.topology[origin] = links
                self.recalculate_routing_table()
                await self.broadcast_to_peers(msg, exclude_peer=sender_name)

    async def broadcast_to_peers(self, message, exclude_peer=None):
        await asyncio.gather(*(self.send_message(w, message) for n, w in self.peers.items() if n != exclude_peer))

    async def update_and_broadcast_lsa(self, force=False):
        if self.unsafe: return
        my_links = {name: random.randint(5, 50) for name in self.peers}
        if self.topology.get(self.name) != my_links or force:
            self.topology[self.name] = my_links
            lsa = self._create_lsa()
            self.logger.info(f"Broadcasting LSA: {lsa}")
            await self.broadcast_to_peers(lsa)
            self.recalculate_routing_table()

    def _create_lsa(self):
        self.sequence_numbers[self.name] += 1
        return {"type": "lsa", "origin": self.name, "seq": self.sequence_numbers[self.name], "links": self.topology.get(self.name, {})}

    def recalculate_routing_table(self):
        self.logger.info(f"Recalculating routes with topology: {self.topology}")
        new_routing_table = {}
        for dest_node in self.topology:
            if dest_node != self.name:
                path, latency = calculate_shortest_path(self.topology, self.name, dest_node)
                if path and len(path) > 1:
                    new_routing_table[dest_node] = {"next_hop": path[1], "latency": latency}
        if self.routing_table != new_routing_table:
            self.routing_table = new_routing_table
            self.logger.info(f"New routing table: {self.routing_table}")

    async def periodic_updater(self):
        while not self.unsafe: await asyncio.sleep(UPDATE_INTERVAL_S); await self.update_and_broadcast_lsa()

    async def scan_for_peers(self):
        await asyncio.sleep(random.uniform(0.1, 1))
        while not self.unsafe:
            self.logger.info(f"Scanning for peers (current: {list(self.peers.keys())})")
            await asyncio.gather(*(self.connect_to_peer(self.host, port) for port in PORT_RANGE))
            await asyncio.sleep(SCAN_INTERVAL)

    async def mark_unsafe(self):
        if self.unsafe: return
        self.logger.warning("DEVICE IS NOW UNSAFE. SHUTTING DOWN.")
        self.unsafe = True
        self.shutdown_event.set()

    async def start(self):
        self.server = await asyncio.start_server(self.handle_connection, self.host, self.port)
        self.logger.info(f"Server started.")

        task_coros = [self.scan_for_peers(), self.periodic_updater()]
        if self.test_unsafe_after > 0:
            async def unsafe_trigger(): await asyncio.sleep(self.test_unsafe_after); await self.mark_unsafe()
            task_coros.append(unsafe_trigger())

        for coro in task_coros:
            task = asyncio.create_task(coro); self.background_tasks.add(task); task.add_done_callback(self.background_tasks.discard)

        await self.shutdown_event.wait()
        await self.stop()

    async def stop(self):
        self.logger.info("Stopping device...")
        for task in self.background_tasks: task.cancel()
        if self.server: self.server.close(); await self.server.wait_closed()
        for writer in self.peers.values():
            if not writer.is_closing(): writer.close()
        self.logger.info("Device stopped.")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name"); parser.add_argument("port", type=int)
    parser.add_argument("--test-unsafe-after", type=int, default=0)
    args = parser.parse_args()
    device = Device(name=args.name, port=args.port, test_unsafe_after=args.test_unsafe_after)
    await device.start()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
