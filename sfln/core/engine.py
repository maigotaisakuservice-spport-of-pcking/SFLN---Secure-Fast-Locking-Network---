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
        await self.mesh.stop()

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

    async def secure_send(self, data, target_peer_id, progress_callback=None):
        if self.should_bypass(): return
        best_route_type = self.router.get_best_route(target_peer_id)
        target_address = self.backbone_addr
        chunks = self.crypto.encrypt_data(data, progress_callback=lambda c, t: progress_callback("ENCRYPTING", c, t) if progress_callback else None)
        await self.protocol.send_data(chunks, target_peer_id, target_address, progress_callback=lambda c, t: progress_callback("TRANSFERRING", c, t) if progress_callback else None)

    def get_status(self):
        return {"node_id": self.node_id, "engine_active": self.is_active}
