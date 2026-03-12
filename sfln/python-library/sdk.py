import sys
import os
import aiohttp
import logging

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sfln.core import SFLNEngine

class SFLNSDK:
    """
    Python SDK for SFLN.
    Now includes Verification Logic to check for local client app presence.
    """
    def __init__(self, master_key=None):
        self.engine = SFLNEngine(master_key)
        self.is_verified = False

    async def verify_app_presence(self):
        """
        Verification Logic: Check if SFLN Daemon (Client App) is running on port 49000.
        """
        async with aiohttp.ClientSession() as session:
            try:
                # Fixed to match gui.py's /status path
                async with session.get('http://localhost:49000/status', timeout=1) as response:
                    self.is_verified = (response.status == 200)
            except:
                self.is_verified = False

        if not self.is_verified:
            logging.warning("[SFLN] Local Client App not detected. Secure features may be limited.")
        return self.is_verified

    async def connect(self, bootstrap_nodes):
        # Even if not verified, we can attempt connecting if standalone
        await self.engine.mesh.discover_peers(bootstrap_nodes)

    async def send(self, data, destination_addr, app_name=None, target_site=None):
        """
        Sends data. SFLN Edge AI automatically determines if
        Direct P2P or Server Relay is best.
        """
        await self.engine.secure_send(data, destination_addr, app_name, target_site)

    def set_exclusions(self, apps=None, sites=None, users=None):
        if apps: self.engine.excluded_apps.update(apps)
        if sites: self.engine.excluded_sites.update(sites)
        if users: self.engine.excluded_users.update(users)

    def get_status(self):
        return self.engine.get_status()
