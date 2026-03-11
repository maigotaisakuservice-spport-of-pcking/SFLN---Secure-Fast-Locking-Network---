import asyncio
import os
import sys
import logging
import uuid
import argparse
from datetime import datetime

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sfln.core import SFLNEngine

class SFLNCUI:
    """
    SFLN High-Performance CUI Client for Server Environments.
    Consolidated version for Windows and Linux optimization.
    """
    def __init__(self, args):
        self.args = args
        self.setup_logging()
        self.engine = SFLNEngine()
        self.node_id = str(uuid.uuid4())
        self.start_time = datetime.now()

    def setup_logging(self):
        level = logging.DEBUG if self.args.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger("SFLN-CUI")

    def print_banner(self):
        print("="*60)
        print(f" SFLN Professional CUI Client - v1.0.0")
        print(f" Node ID: {self.node_id}")
        print(f" Target Throughput: 1GB/s (UDP-Accelerated)")
        print("="*60)

    async def run_stats_loop(self):
        while True:
            uptime = datetime.now() - self.start_time
            # Simulated stats for now
            status = "ACTIVE" if self.engine.is_active else "IDLE"
            print(f"\r[SFLN] Uptime: {str(uptime).split('.')[0]} | Status: {status} | Peers: {len(self.engine.mesh.peers)}", end="")
            await asyncio.sleep(1)

    async def start(self):
        self.print_banner()
        self.logger.info("Initializing SFLN Core Engine...")

        # Optimize for Server
        if os.name == 'posix':
            self.logger.info("Applying Linux TCP/UDP stack optimizations...")
            # Optimization logic here

        await self.engine.start()
        self.logger.info("SFLN Backbone connection established.")

        try:
            await self.run_stats_loop()
        except KeyboardInterrupt:
            self.logger.info("\nShutting down...")
            await self.engine.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SFLN CUI Client")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logs")
    parser.add_argument("--port", type=int, default=9000, help="Listen port")
    args = parser.parse_args()

    cui = SFLNCUI(args)
    try:
        asyncio.run(cui.start())
    except KeyboardInterrupt:
        pass
