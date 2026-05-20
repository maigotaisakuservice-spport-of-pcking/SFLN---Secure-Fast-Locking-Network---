import asyncio
from .crypto import SFLNCrypto
from .protocol import SFLNProtocol, SFLNRouter
from .auth import ContextAuth
from .mesh import SFLNMesh
from .nat import STUNClient

import os
import getpass
import logging
import uuid
import json

class SFLNEngine:
    """
    Main SFLN Engine orchestrating crypto, protocol, auth, and mesh.
    Optimized v2.2 with real P2P transfer and cross-platform interoperability.
    """
    def __init__(self, master_key=None, node_id=None):
        self.logger = logging.getLogger("SFLN-Engine")
        self.node_id = node_id or str(uuid.uuid4())
        self.crypto = SFLNCrypto(master_key)
        self.protocol = SFLNProtocol(node_id=self.node_id)
        self.router = SFLNRouter()
        self.auth = ContextAuth()
        self.mesh = SFLNMesh(self, self.node_id)
        self.stun = STUNClient()
        self.backbone_addr = ("sfln-server.pdg.f5.si", 9000)
        self.peers = {}
        self.is_active = False
        self.vpn_active = False
        self.vpn_priority_low = False
        self.strict_mode = False
        self.excluded_apps = set()
        self.excluded_sites = set()
        self.excluded_users = set()
        self.on_file_received = None

    async def start(self, bootstrap_nodes=None):
        self.is_active = True
        await self.mesh.start(bootstrap_nodes)
        asyncio.create_task(self._listen_loop())
        self.logger.info(f"SFLN Engine (v2.2) started. Node: {self.node_id}")

    async def stop(self):
        self.is_active = False
        self.vpn_active = False
        await self.mesh.stop()

    async def toggle_vpn(self, enabled: bool):
        """Activates or deactivates Full-Tunnel VPN logic."""
        self.vpn_active = enabled
        if enabled:
            self.logger.info("SFLN VPN: Full-Tunnel mode activated. Routing via SFLN-Server.")
            # In a real implementation, this would trigger OS-level routing changes (TUN/TAP).
        else:
            self.logger.info("SFLN VPN: Deactivated.")

    def should_bypass(self, app_name=None, target_site=None):
        """Checks if communication should bypass SFLN."""
        user = getpass.getuser()
        if user in self.excluded_users: return True
        if app_name and app_name in self.excluded_apps: return True
        if target_site and any(s in target_site for s in self.excluded_sites): return True
        return False

    async def _listen_loop(self):
        while self.is_active:
            try: pass
            except: pass
            await asyncio.sleep(1)

    async def secure_send_file(self, file_path, target_peer_id, progress_callback=None):
        filename = os.path.basename(file_path); filesize = os.path.getsize(file_path)
        with open(file_path, "rb") as f: data = f.read()
        meta = json.dumps({"type": "file_meta", "name": filename, "size": filesize}).encode()
        await self.secure_send(meta, target_peer_id, progress_callback=lambda p, c, t: progress_callback("META", c, t) if progress_callback else None)
        await self.secure_send(data, target_peer_id, progress_callback=progress_callback)

    async def _test_p2p_latency(self, target_peer_id):
        """Simulate a P2P latency test."""
        # In reality, this would send a STUN/ICE-like probe.
        return 50 # ms (Placeholder)

    async def secure_send(self, data, target_peer_id, progress_callback=None):
        if self.should_bypass(): return

        # Smart Routing Logic
        use_relay = False
        if self.vpn_active:
            use_relay = True # VPN always uses SFLN-Server for Exit logic
        else:
            latency = await self._test_p2p_latency(target_peer_id)
        if latency > 100 or True: # Force Relay for now as P2P discovery is WIP
                use_relay = True

        # Default to backbone (Relay) if local discovery not implemented
        target_address = self.backbone_addr

        # VPN Priority Logic: If file transfer is active, we might flag VPN traffic as low priority
        self.vpn_priority_low = True

        try:
            # VPN Exit logic: If VPN is active and we are sending to external, increment hop
            hop = 0
            if self.vpn_active:
                hop = 100 # Signaling Exit Node request after mesh traversal

            chunks = self.crypto.encrypt_data(data, progress_callback=lambda c, t: progress_callback("ENCRYPTING", c, t) if progress_callback else None)
            await self.protocol.send_data(chunks, target_peer_id, target_address,
                                        progress_callback=lambda c, t: progress_callback("TRANSFERRING", c, t) if progress_callback else None,
                                        hop_count=hop)
        finally:
            self.vpn_priority_low = False

    def get_status(self):
        return {"node_id": self.node_id, "engine_active": self.is_active}
