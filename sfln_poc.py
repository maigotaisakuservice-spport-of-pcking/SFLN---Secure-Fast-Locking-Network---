import asyncio
import json
import logging
import random
import time
import heapq
import os
import sys
from collections import defaultdict
from base64 import b64encode, b64decode

# --- Global Configuration ---
HOST = '127.0.0.1'
UPDATE_INTERVAL = 5
SCAN_INTERVAL = 3
LOW_POWER_LATENCY_PENALTY = 1000

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
log = logging.getLogger("TestRunner")

# --- Feature D (Simulated Quantum Resistance) ---
class Kyber512:
    @staticmethod
    def generate_keypair(): return (b'pk' + os.urandom(8), b'sk' + os.urandom(8))
    @staticmethod
    def encapsulate(pk):
        ss = b'ss' + os.urandom(8)
        return (b'ct_for_' + pk[:4], ss), ss
    @staticmethod
    def decapsulate(sk, ct): return b'ss' + os.urandom(8)

# --- Feature C (Routing Algorithm) ---
def calculate_shortest_path(graph, start, end):
    distances = {node: float('inf') for node in graph}
    distances[start] = 0
    previous_nodes = {node: None for node in graph}
    pq = [(0, start)]
    while pq:
        dist, current = heapq.heappop(pq)
        if dist > distances[current]: continue
        if current == end: break
        for neighbor, weight in graph.get(current, {}).items():
            if neighbor not in graph: continue
            distance = dist + weight
            if distance < distances.get(neighbor, float('inf')):
                distances[neighbor] = distance
                previous_nodes[neighbor] = current
                heapq.heappush(pq, (distance, neighbor))
    path, curr = [], end
    if distances.get(curr) == float('inf'): return None, float('inf')
    while curr is not None:
        path.insert(0, curr)
        curr = previous_nodes.get(curr)
    return (path, distances[end]) if path and path[0] == start else (None, float('inf'))

# --- Main Device Class (Features B, C, D, E, F) ---
class Device:
    def __init__(self, name, port, context, policy, power_mode):
        self.name, self.port, self.context, self.auth_policy, self.power_mode = name, port, context, policy, power_mode
        self.host, self.peers, self.shutdown_event = HOST, {}, asyncio.Event()
        self.tasks = set()
        self.kyber_pk, self.kyber_sk = Kyber512.generate_keypair()
        self.topology, self.sequence_numbers, self.routing_table = {self.name: {}}, defaultdict(int), {}
        self.logger = logging.getLogger(f"Device-{self.name}")

    async def send_message(self, writer, message):
        try:
            if writer.is_closing(): return
            writer.write((json.dumps(message) + '\n').encode()); await writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError): pass

    async def broadcast_to_peers(self, message, exclude_peer=None):
        await asyncio.gather(*(self.send_message(w, message) for n, w in self.peers.items() if n != exclude_peer), return_exceptions=True)

    async def _cleanup_peer(self, peer_name, writer):
        if peer_name and self.peers.pop(peer_name, None):
            self.logger.info(f"Peer '{peer_name}' disconnected. Current peers: {list(self.peers.keys())}")
            self.topology.get(self.name, {}).pop(peer_name, None)
            await self.update_and_broadcast_lsa(force=True)
        if writer and not writer.is_closing():
            writer.close()
            try: await writer.wait_closed()
            except: pass

    def _is_context_valid(self, peer_context):
        for key, required in self.auth_policy.items():
            if required != "any" and peer_context.get(key) != required:
                self.logger.warning(f"Auth failed for peer: context {peer_context} failed policy on key '{key}'.")
                return False
        return True

    async def _handle_connection(self, reader, writer):
        peer_name = None
        try:
            data = await asyncio.wait_for(reader.readline(), 5.0)
            msg = json.loads(data.decode())
            peer_name = msg.get('name')
            if msg.get('type') != 'hello' or not peer_name: return

            if not self._is_context_valid(msg.get('context')): return
            if peer_name in self.peers: return # Already connected, simple drop

            self.peers[peer_name] = writer
            self.logger.info(f"Connection from '{peer_name}' established.")

            # Simulate Kyber exchange
            self.logger.info(f"Kyber handshake with '{peer_name}' completed.")

            await self.update_and_broadcast_lsa(force=True)
            await self.message_loop(reader, peer_name)
        except Exception: pass
        finally: await self._cleanup_peer(peer_name, writer)

    async def connect_to_peer(self, devices_config, remote_name):
        if self.shutdown_event.is_set() or remote_name == self.name or remote_name in self.peers: return

        writer = None
        try:
            config = devices_config[remote_name]
            if not self._is_context_valid(config['context']): return

            reader, writer = await asyncio.open_connection(self.host, config['port'])
            await self.send_message(writer, {"type": "hello", "name": self.name, "context": self.context})
            self.peers[remote_name] = writer
            self.logger.info(f"Connection to '{remote_name}' established.")
            await self.update_and_broadcast_lsa(force=True)
            await self.message_loop(reader, remote_name)
        except (ConnectionRefusedError, asyncio.TimeoutError): pass
        finally: await self._cleanup_peer(remote_name, writer)

    async def message_loop(self, reader, peer_name):
        while not self.shutdown_event.is_set():
            try:
                line = await reader.readline()
                if not line: break
                msg = json.loads(line.decode())
                if msg.get("type") == "lsa":
                    origin, seq, links = msg.get("origin"), msg.get("seq"), msg.get("links", {})
                    if origin != self.name and seq > self.sequence_numbers[origin]:
                        self.topology[origin] = links; self.sequence_numbers[origin] = seq
                        self.recalculate_routing_table()
                        await self.broadcast_to_peers(msg, exclude_peer=peer_name)
            except (asyncio.IncompleteReadError, ConnectionResetError, json.JSONDecodeError): break

    async def update_and_broadcast_lsa(self, force=False):
        if self.shutdown_event.is_set(): return
        penalty = LOW_POWER_LATENCY_PENALTY if self.power_mode == 'low' else 0
        my_links = {name: random.randint(5, 50) + penalty for name in self.peers}

        if self.topology.get(self.name) != my_links or force:
            self.topology[self.name] = my_links
            lsa = {"type": "lsa", "origin": self.name, "seq": int(time.time()), "links": self.topology[self.name]}
            self.logger.info(f"Broadcasting LSA.")
            await self.broadcast_to_peers(lsa)
            self.recalculate_routing_table()

    def recalculate_routing_table(self):
        self.logger.info(f"Recalculating routes with topology: {json.dumps(self.topology)}")
        new_table = {dest: {"next_hop": path[1], "latency": lat} for dest, (path, lat) in
                     ((d, calculate_shortest_path(self.topology, self.name, d)) for d in self.topology if d != self.name) if path and len(path) > 1}
        if self.routing_table != new_table:
            self.routing_table = new_table
            self.logger.info(f"New routing table: {self.routing_table}")

    async def discover_peers(self, devices_config):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(SCAN_INTERVAL)
            await asyncio.gather(*(self.connect_to_peer(devices_config, name) for name in devices_config))

    async def periodic_updater(self):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(UPDATE_INTERVAL)
            await self.update_and_broadcast_lsa()

    async def start(self, devices_config, shutdown_timer=0):
        self.server = await asyncio.start_server(self._handle_connection, self.host, self.port)
        self.logger.info(f"Server started.")

        self.tasks.add(asyncio.create_task(self.discover_peers(devices_config)))
        self.tasks.add(asyncio.create_task(self.periodic_updater()))

        if shutdown_timer > 0:
            async def trigger():
                await asyncio.sleep(shutdown_timer)
                self.logger.warning("TEST: Marking as unsafe and shutting down.")
                self.shutdown_event.set()
            self.tasks.add(asyncio.create_task(trigger()))

        await self.shutdown_event.wait()

        self.server.close()
        for task in self.tasks: task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.server.wait_closed()
        self.logger.info("Device stopped.")

async def test_main():
    log.info("--- SFLN Advanced Features Test ---")
    TEST_CONFIG = {
        "Device-A": {"port": 9001, "context": {"location": "office"}, "policy": {"location": "office"}, "power_mode": "normal"},
        "Device-B": {"port": 9002, "context": {"location": "office"}, "policy": {"location": "office"}, "power_mode": "normal"},
        "Device-C": {"port": 9003, "context": {"location": "office"}, "policy": {"location": "office"}, "power_mode": "low"},
        "Device-D": {"port": 9004, "context": {"location": "home"},   "policy": {"location": "office"}, "power_mode": "normal"}
    }
    NODE_TO_DROP = "Device-C"
    UNSAFE_TIMER_S = 15
    PHASE_1_DURATION = 10
    PHASE_2_DURATION = 10

    devices = {name: Device(name, **cfg) for name, cfg in TEST_CONFIG.items()}
    tasks = [asyncio.create_task(dev.start(TEST_CONFIG, UNSAFE_TIMER_S if dev.name == NODE_TO_DROP else 0)) for dev in devices.values()]

    log.info(f"\n[PHASE 1] Network forming. Waiting {PHASE_1_DURATION}s...")
    await asyncio.sleep(PHASE_1_DURATION)

    log.info("\n--- Verifying Phase 1 ---")
    trusted_nodes = {"Device-A", "Device-B", "Device-C"}
    assert set(devices["Device-A"].peers.keys()) == trusted_nodes - {"Device-A"}, "A failed to connect to all trusted peers"
    log.info("✅ Device-A connected to B, C")
    assert set(devices["Device-B"].peers.keys()) == trusted_nodes - {"Device-B"}, "B failed to connect to all trusted peers"
    log.info("✅ Device-B connected to A, C")
    assert set(devices["Device-C"].peers.keys()) == trusted_nodes - {"Device-C"}, "C connected to A, B"
    log.info("✅ Trusted nodes formed a full mesh.")
    assert not devices["Device-D"].peers, "Untrusted Device-D should have no peers"
    log.info("✅ Untrusted node (Device-D) is isolated (Feature E).")
    assert "Kyber" in [h.getMessage() for h in log.handlers[0].root.manager.loggerDict['Device-A'].handlers[0].formatter._fmt]
    log.info("✅ Kyber handshake simulation completed (Feature D).")
    assert devices["Device-A"].routing_table.get("Device-C") and devices["Device-A"].routing_table["Device-C"]["latency"] > 1000, "Device-A should see high latency for Device-C"
    log.info("✅ Low power mode correctly affects routing tables (Feature F).")
    log.info("--- Phase 1 Verification Passed ---")

    log.info(f"\n[PHASE 2] Waiting for '{NODE_TO_DROP}' to go offline...")
    await asyncio.sleep(UNSAFE_TIMER_S - PHASE_1_DURATION + 3)

    log.info("\n--- Verifying Phase 2 ---")
    remaining_nodes = trusted_nodes - {NODE_TO_DROP}
    assert devices[NODE_TO_DROP].shutdown_event.is_set()
    log.info(f"✅ {NODE_TO_DROP} has shut down.")
    await asyncio.sleep(2)
    for name in remaining_nodes:
        assert NODE_TO_DROP not in devices[name].peers
        assert set(devices[name].peers.keys()) == remaining_nodes - {name}
    log.info("✅ All remaining nodes dropped the unsafe peer and have correct peer lists.")
    assert "Device-C" not in devices["Device-A"].routing_table
    log.info("✅ Device-A's routing table is updated.")

    log.info("\n\n✅✅✅ OVERALL RESULT: SUCCESS ✅✅✅")

    for t in tasks: t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    try: asyncio.run(test_main())
    except Exception as e: log.error(f"Test failed: {e}", exc_info=True)
