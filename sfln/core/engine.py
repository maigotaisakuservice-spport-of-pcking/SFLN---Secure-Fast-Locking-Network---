import asyncio
from .crypto import SFLNCrypto
from .protocol import SFLNProtocol, SFLNRouter
from .auth import ContextAuth
from .mesh import SFLNMesh
from .nat import STUNClient

import os
import getpass
import logging

class SFLNEngine:
    """
    Main SFLN Engine orchestrating crypto, protocol, auth, and mesh.
    Includes exclusion logic for apps, sites, and users.
    """
    def __init__(self, master_key=None, node_id=None):
        self.logger = logging.getLogger("SFLN-Engine")
        self.crypto = SFLNCrypto(master_key)
        self.protocol = SFLNProtocol()
        self.router = SFLNRouter()
        self.auth = ContextAuth()
        self.mesh = SFLNMesh(self, node_id)
        self.stun = STUNClient()
        self.backbone_addr = ("127.0.0.1", 9000) # Default backbone
        self.peers = {}

        # Exclusion settings
        self.excluded_apps = set()
        self.excluded_sites = set()
        self.excluded_users = set()
        self.is_active = False

    async def start(self, bootstrap_nodes=None):
        """Start all SFLN engine services."""
        self.is_active = True
        await self.mesh.start(bootstrap_nodes)
        self.logger.info("SFLN Engine fully started.")

    async def stop(self):
        """Stop all SFLN engine services."""
        self.is_active = False
        await self.mesh.stop()
        self.logger.info("SFLN Engine stopped.")

    def should_bypass(self, app_name=None, target_site=None):
        """Checks if the communication should bypass SFLN based on exclusions."""
        current_user = getpass.getuser()
        if current_user in self.excluded_users:
            return True
        if app_name and app_name in self.excluded_apps:
            return True
        if target_site and any(site in target_site for site in self.excluded_sites):
            return True
        return False

    async def secure_send(self, data, target_peer_id, app_name=None, target_site=None):
        """
        Encrypt and send data securely using AI-driven dynamic routing.
        Selects best path (P2P, TURN, Backbone) based on network metrics.
        """
        if self.should_bypass(app_name, target_site):
            self.logger.info(f"Bypassing SFLN for {app_name or target_site or 'current user'}")
            return

        # 1. AI Decision: Determine the best route for this peer
        best_route_type = self.router.get_best_route(target_peer_id)

        # 2. Select target address based on AI decision
        target_address = None
        if best_route_type == "direct":
            # Look up in mesh for direct P2P address
            peer_info = self.mesh.peers.get(target_peer_id)
            if peer_info:
                target_address = peer_info['addr']
            else:
                best_route_type = "backbone" # Fallback to backbone

        if best_route_type == "backbone":
            target_address = self.backbone_addr

        if not target_address:
            self.logger.error(f"No route found for peer {target_peer_id}")
            return

        self.logger.info(f"AI Routing selected path: {best_route_type} for peer {target_peer_id}")

        # 3. Encryption and 1KB chunking
        chunks = self.crypto.encrypt_data(data)
        protocol_chunks = []
        for i, chunk in enumerate(chunks):
            # Binary protocol header: [Chunk Index (4b)]
            protocol_chunks.append(i.to_bytes(4, 'big') + chunk)

        # 4. Multi-stream high-speed transmission
        await self.protocol.send_data(protocol_chunks, target_address)

    async def secure_receive(self, expected_chunks_count):
        """Receive and decrypt data."""
        encrypted_chunks = await self.protocol.receive_data(expected_chunks_count)
        return self.crypto.decrypt_chunks(encrypted_chunks)

    def get_status(self):
        return {
            "key_bits": self.crypto.KEY_BITS,
            "peers_count": len(self.peers),
            "engine_active": True
        }
