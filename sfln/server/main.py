import asyncio
import logging
import sys
import os
import json
import uuid

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sfln.core import SFLNEngine

class SFLNServer:
    """
    SFLN High-Performance Backbone Server.
    Supports both JSON control channel and Binary high-speed data relay.
    """
    def __init__(self, port=9000):
        self.port = port
        self.engine = SFLNEngine()
        self.peers = {} # {node_id_bytes: addr}
        self.logger = logging.getLogger("SFLN-Server")
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    async def start(self):
        self.logger.info(f"SFLN Professional Server starting on port {self.port}")
        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: SFLNServerProtocol(self),
            local_addr=('0.0.0.0', self.port)
        )
        try:
            await asyncio.Future()
        finally:
            self.transport.close()

class SFLNServerProtocol(asyncio.DatagramProtocol):
    def __init__(self, server):
        self.server = server
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if not data: return

        # High-Speed Binary Relay Path
        # Format: [Magic: 'S' (1b)][Type: 0x01 (1b)][TargetID (16b)][Payload]
        if data[0] == 0x53 and len(data) > 18:
            msg_type = data[1]
            if msg_type == 0x01: # RELAY
                target_id = data[2:18]
                if target_id in self.server.peers:
                    # Forward payload with minimal overhead
                    # We wrap it with [Magic][Type: 0x02 (Relayed)][SourceAddr (not used for now)][Payload]
                    relay_packet = bytearray([0x53, 0x02]) + data[18:]
                    self.transport.sendto(relay_packet, self.server.peers[target_id])
                return

        # Control Channel (JSON)
        try:
            if data.startswith(b'{'):
                msg = json.loads(data.decode())
                mtype = msg.get("type")

                if mtype == "register":
                    node_id_str = msg.get("node_id")
                    # Convert UUID string to 16 bytes for binary efficiency
                    node_id_bytes = uuid.UUID(node_id_str).bytes
                    self.server.peers[node_id_bytes] = addr
                    self.server.logger.info(f"Registered node {node_id_str} at {addr}")
                    self.transport.sendto(json.dumps({"type": "reg_ack"}).encode(), addr)

                elif mtype == "get_peers":
                    # Return list of active node IDs
                    peers_list = [str(uuid.UUID(bytes=nid)) for nid in self.server.peers.keys()]
                    self.transport.sendto(json.dumps({"type": "peers", "list": peers_list}).encode(), addr)
        except Exception as e:
            self.server.logger.error(f"Error handling control packet: {e}")

if __name__ == "__main__":
    server = SFLNServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass
