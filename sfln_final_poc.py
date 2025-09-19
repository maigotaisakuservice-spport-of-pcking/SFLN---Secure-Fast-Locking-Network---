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

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
log = logging.getLogger("TestRunner")

# --- Feature D (Simulated Quantum Resistance) ---
try:
    from kyber import Kyber512
    log.info("Successfully imported `kyber-py` library.")
except ImportError:
    log.warning("`kyber-py` not found. Using dummy class for quantum crypto simulation.")
    class Kyber512:
        @staticmethod
        def generate_keypair(): return (b'pk' + os.urandom(8), b'sk' + os.urandom(8))
        @staticmethod
        def encapsulate(pk): return (b'ct' + os.urandom(8), b'ss' + os.urandom(8))
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
            if neighbor not in graph: continue # Ignore links to nodes not in our known topology
            distance = dist + weight
            if distance < distances.get(neighbor, float('inf')):
                distances[neighbor] = distance
                previous_nodes[neighbor] = current
                heapq.heappush(pq, (distance, neighbor))
    path = []
    curr = end
    if distances.get(curr) == float('inf'): return None, float('inf')
    while curr is not None:
        path.insert(0, curr)
        curr = previous_nodes.get(curr)
    return (path, distances[end]) if path and path[0] == start else (None, float('inf'))

# --- Features B, C, D, E, F (Device Logic) ---
class Device:
    def __init__(self, name, port, context, policy, power_mode):
        self.name, self.port, self.context, self.auth_policy, self.power_mode = name, port, context, policy, power_mode
        self.host, self.peers, self.shutdown_event = '127.0.0.1', {}, asyncio.Event()
        self.tasks = set()
        self.kyber_pk, self.kyber_sk = Kyber512.generate_keypair()
        self.topology, self.sequence_numbers = {self.name: {}}, defaultdict(int)
        self.routing_table = {}
        self.logger = logging.getLogger(f"Device-{self.name}")
        self.logger.info(f"Initialized. Policy: {self.auth_policy}, Context: {self.context}, Power: {self.power_mode}")

    async def send_message(self, writer, message):
        try:
            if writer.is_closing(): return
            writer.write((json.dumps(message) + '\n').encode())
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError): pass

    async def broadcast_to_peers(self, message, exclude_peer=None):
        await asyncio.gather(*(self.send_message(w, message) for n, w in self.peers.items() if n != exclude_peer), return_exceptions=True)

    async def _cleanup_peer(self, peer_name, writer):
        if peer_name and self.peers.pop(peer_name, None):
            self.logger.info(f"Peer '{peer_name}' removed. Current peers: {list(self.peers.keys())}")
            if peer_name in self.topology.get(self.name, {}):
                del self.topology[self.name][peer_name]
                await self.update_and_broadcast_lsa(force=True)
        if writer and not writer.is_closing():
            writer.close()
            try: await writer.wait_closed()
            except: pass

    def _is_context_valid(self, peer_context):
        if not peer_context: return False
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
            if not self._is_context_valid(msg.get('context')): return

            # Tie-breaker
            if self.name < peer_name:
                self.logger.warning(f"Tie-break: My name ('{self.name}') is smaller. Dropping incoming from '{peer_name}'.")
                return

            if peer_name in self.peers: return

            self.logger.info(f"Accepted connection from '{peer_name}'.")
            await self.send_message(writer, {"type": "ack", "name": self.name})
            self.peers[peer_name] = writer
            self.logger.info(f"Peers: {list(self.peers.keys())}")
            await self.update_and_broadcast_lsa(force=True)
            await self.message_loop(reader, writer, peer_name)
        except Exception as e: self.logger.debug(f"Incoming handler failed: {e}")
        finally: await self._cleanup_peer(peer_name, writer)

    async def connect_to_peer(self, devices_config, remote_name):
        if self.shutdown_event.is_set() or remote_name == self.name or remote_name in self.peers: return
        if self.name > remote_name: return # Tie-breaker

        writer = None
        try:
            config = devices_config[remote_name]
            reader, writer = await asyncio.open_connection(self.host, config['port'])
            await self.send_message(writer, {"type": "hello", "name": self.name, "context": self.context})

            data = await asyncio.wait_for(reader.readline(), 5.0)
            ack_msg = json.loads(data.decode())
            if ack_msg.get('type') != 'ack': raise ValueError("Expected ack")

            self.logger.info(f"Connection to '{remote_name}' established.")
            self.peers[remote_name] = writer
            await self.update_and_broadcast_lsa(force=True)
            await self.message_loop(reader, writer, remote_name)
        except Exception as e: self.logger.debug(f"Could not connect to {remote_name}: {e}")
        finally: await self._cleanup_peer(remote_name, writer)

    async def message_loop(self, reader, peer_name):
        while not self.shutdown_event.is_set() and peer_name in self.peers:
            try:
                line = await reader.readline()
                if not line: break
                await self.handle_message(json.loads(line.decode()), peer_name)
            except (asyncio.IncompleteReadError, ConnectionResetError, json.JSONDecodeError): break
        await self._cleanup_peer(peer_name, self.peers.get(peer_name))

    async def handle_message(self, msg, sender_name):
        msg_type = msg.get("type")
        if msg_type == "lsa":
            origin, seq, links = msg.get("origin"), msg.get("seq"), msg.get("links", {})
            if origin != self.name and seq > self.sequence_numbers[origin]:
                self.topology[origin] = links
                self.sequence_numbers[origin] = seq
                self.recalculate_routing_table()
                await self.broadcast_to_peers(msg, exclude_peer=sender_name)

    async def update_and_broadcast_lsa(self, force=False):
        if self.shutdown_event.is_set(): return
        penalty = 1000 if self.power_mode == 'low' else 0
        my_links = {name: random.randint(5, 50) + penalty for name in self.peers}

        if self.topology.get(self.name) != my_links or force:
            self.topology[self.name] = my_links
            lsa = {"type": "lsa", "origin": self.name, "seq": int(time.time()), "links": self.topology[self.name]}
            self.logger.info(f"Broadcasting LSA: {lsa}")
            await self.broadcast_to_peers(lsa)
            self.recalculate_routing_table()

    def recalculate_routing_table(self):
        self.logger.info(f"Recalculating routes with topology: {json.dumps(self.topology)}")
        new_routing_table = {}
        for dest_node in self.topology:
            if dest_node != self.name:
                path, latency = calculate_shortest_path(self.topology, self.name, dest_node)
                if path and len(path) > 1: new_routing_table[dest_node] = {"next_hop": path[1], "latency": latency}
        if self.routing_table != new_routing_table:
            self.routing_table = new_routing_table
            self.logger.info(f"New routing table: {self.routing_table}")

    async def discover_peers(self, devices_config):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(SCAN_INTERVAL)
            self.logger.info(f"Scanning for peers (current: {list(self.peers.keys())})")
            await asyncio.gather(*(self.connect_to_peer(devices_config, name) for name in devices_config))

    async def start(self, devices_config, shutdown_timer=0):
        self.server = await asyncio.start_server(self._handle_connection, self.host, self.port)
        self.logger.info(f"Server started.")

        self.tasks.add(asyncio.create_task(self.discover_peers(devices_config)))
        self.tasks.add(asyncio.create_task(self.periodic_updater()))

        if shutdown_timer > 0:
            async def trigger():
                await asyncio.sleep(shutdown_timer)
                self.logger.warning("TEST: Marking as unsafe.")
                self.shutdown_event.set()
            self.tasks.add(asyncio.create_task(trigger()))

        await self.shutdown_event.wait()

        self.logger.info("Shutdown initiated.")
        self.server.close()
        for task in self.tasks: task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.server.wait_closed()
        self.logger.info("Device stopped.")

    async def periodic_updater(self):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(UPDATE_INTERVAL)
            await self.update_and_broadcast_lsa()

async def test_main():
    log.info("--- SFLN Advanced Features Test ---")
    TEST_CONFIG = {
        "Device-A": {"port": 9001, "context": {"location": "office"}, "policy": {"allowed_location": "office"}, "power_mode": "normal"},
        "Device-B": {"port": 9002, "context": {"location": "office"}, "policy": {"allowed_location": "office"}, "power_mode": "normal"},
        "Device-C": {"port": 9003, "context": {"location": "office"}, "policy": {"allowed_location": "office"}, "power_mode": "low"},
        "Device-D": {"port": 9004, "context": {"location": "home"},   "policy": {"allowed_location": "office"}, "power_mode": "normal"}
    }
    NODE_TO_DROP = "Device-C"
    UNSAFE_TIMER_S = 15
    PHASE_1_DURATION = 12
    PHASE_2_DURATION = 12

    devices = {name: Device(name, **cfg) for name, cfg in TEST_CONFIG.items()}
    tasks = [asyncio.create_task(dev.start(TEST_CONFIG, UNSAFE_TIMER_S if dev.name == NODE_TO_DROP else 0)) for dev in devices.values()]

    log.info(f"\n[PHASE 1] Network forming. Waiting {PHASE_1_DURATION}s...")
    await asyncio.sleep(PHASE_1_DURATION)

    log.info("\n--- Verifying Phase 1 ---")
    trusted_nodes = {"Device-A", "Device-B", "Device-C"}
    assert set(devices["Device-A"].peers.keys()) == trusted_nodes - {"Device-A"}
    log.info("✅ Device-A connected to B, C")
    assert set(devices["Device-B"].peers.keys()) == trusted_nodes - {"Device-B"}
    log.info("✅ Device-B connected to A, C")
    assert set(devices["Device-C"].peers.keys()) == trusted_nodes - {"Device-C"}
    log.info("✅ Device-C connected to A, B")
    log.info("✅ Trusted nodes formed a full mesh.")
    assert not devices["Device-D"].peers
    log.info("✅ Untrusted node (Device-D) is isolated (Feature E).")
    # A less brittle check for latency
    assert devices["Device-A"].routing_table.get("Device-C") and devices["Device-A"].routing_table["Device-C"]["latency"] > 1000
    log.info("✅ Low power mode correctly affects routing tables (Feature F).")
    log.info("--- Phase 1 Verification Passed ---")

    log.info(f"\n[PHASE 2] Waiting for '{NODE_TO_DROP}' to go offline...")
    await asyncio.sleep(UNSAFE_TIMER_S - PHASE_1_DURATION + 3)

    log.info("\n--- Verifying Phase 2 ---")
    remaining_nodes = trusted_nodes - {NODE_TO_DROP}
    assert devices[NODE_TO_DROP].shutdown_event.is_set()
    log.info(f"✅ {NODE_TO_DROP} has shut down.")
    # Allow a moment for connections to fully close and be removed
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
    try:
        asyncio.run(test_main())
    except Exception as e:
        log.error(f"Test failed: {e}", exc_info=True)
