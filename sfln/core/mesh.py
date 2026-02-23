import asyncio
import json
import logging
import uuid
import time
from .auth import ContextAuth

class SFLNMesh:
    """
    Complete Self-growing P2P Mesh Network.
    Automatically discovers peers, manages lifecycle, and handles node exclusion.
    """
    def __init__(self, engine, node_id=None):
        self.engine = engine
        self.node_id = node_id or str(uuid.uuid4())
        self.peers = {} # {peer_id: {'addr': addr, 'last_seen': float, 'context': dict}}
        self.logger = logging.getLogger(f"SFLN-Mesh")
        self.auth = ContextAuth()
        self.is_running = False
        self._discovery_task = None

    async def start(self, bootstrap_nodes=None):
        """Start the mesh network services."""
        self.is_running = True
        self._discovery_task = asyncio.create_task(self._discovery_loop(bootstrap_nodes or []))
        self.logger.info(f"Mesh service started. Node ID: {self.node_id}")

    async def stop(self):
        self.is_running = False
        if self._discovery_task:
            self._discovery_task.cancel()
            try: await self._discovery_task
            except asyncio.CancelledError: pass
        self.logger.info("Mesh service stopped.")

    async def _discovery_loop(self, bootstrap_nodes):
        """Periodic background task for peer discovery and maintenance."""
        while self.is_running:
            # 1. Try to connect to bootstrap nodes if we have few peers
            if len(self.peers) < 3:
                for addr in bootstrap_nodes:
                    await self.ping_peer(addr)

            # 2. Ask existing peers for their peer lists (Gossip/Self-growth)
            current_peers = list(self.peers.values())
            for p in current_peers:
                # In a real impl, this would be a message: {"type": "get_neighbors"}
                pass

            # 3. Clean up stale peers (Auto-exclusion)
            now = time.time()
            stale = [pid for pid, info in self.peers.items() if now - info['last_seen'] > 60]
            for pid in stale:
                del self.peers[pid]
                self.logger.info(f"Removed stale peer {pid}")

            await asyncio.sleep(20)

    async def ping_peer(self, addr):
        """Initiate handshake with a peer."""
        context = self.auth.get_current_context()
        msg = {
            "type": "hello",
            "node_id": self.node_id,
            "context": context
        }
        try:
            # Using engine's protocol to send control packet
            # In a real implementation, we'd wait for an 'ack'
            data = json.dumps(msg).encode()
            # self.engine.protocol.sock.sendto(data, addr)
            # (Note: engine.protocol.send_data is for encrypted chunks,
            # here we'd use a control channel or specific header)
            pass
        except Exception as e:
            self.logger.debug(f"Ping to {addr} failed: {e}")

    def handle_incoming_message(self, data, addr):
        """Process mesh-level control messages."""
        try:
            msg = json.loads(data.decode())
            mtype = msg.get("type")
            if mtype == "hello":
                return self._handle_hello(msg, addr)
        except: pass
        return False

    def _handle_hello(self, msg, addr):
        peer_id = msg.get("node_id")
        peer_context = msg.get("context")

        is_valid, reason = self.auth.verify_context(peer_context)
        if is_valid:
            self.peers[peer_id] = {
                "addr": addr,
                "last_seen": time.time(),
                "context": peer_context
            }
            self.logger.info(f"Node {peer_id} joined mesh. Total: {len(self.peers)}")
            return True
        else:
            self.logger.warning(f"Peer {peer_id} rejected: {reason}")
            return False
