import sys
import os

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sfln.core import SFLNEngine

class SFLNSDK:
    """
    Python SDK for SFLN.
    Easy to use interface for applications to join SFLN and send/receive data.
    """
    def __init__(self, master_key=None):
        self.engine = SFLNEngine(master_key)

    async def connect(self, bootstrap_nodes):
        """Connect to the SFLN network."""
        await self.engine.mesh.discover_peers(bootstrap_nodes)

    async def send(self, data, destination_addr, app_name=None, target_site=None):
        """Send data securely via SFLN, respecting exclusion settings."""
        await self.engine.secure_send(data, destination_addr, app_name, target_site)

    def set_exclusions(self, apps=None, sites=None, users=None):
        """Configure exclusion settings."""
        if apps: self.engine.excluded_apps.update(apps)
        if sites: self.engine.excluded_sites.update(sites)
        if users: self.engine.excluded_users.update(users)

    def get_status(self):
        """Get current network and engine status."""
        return self.engine.get_status()
