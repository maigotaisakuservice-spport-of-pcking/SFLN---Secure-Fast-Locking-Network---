import asyncio
import logging
import sys
import os
import json
import uuid
import websockets

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sfln.core import SFLNEngine

class SFLNServer:
    def __init__(self, port=9000, ws_port=9001, log_level=logging.INFO):
        self.port = port
        self.ws_port = ws_port
        self.engine = SFLNEngine()
        self.udp_peers = {} # {node_id_bytes: addr}
        self.ws_peers = {}  # {node_id_bytes: (websocket, node_id_str)}
        self.logger = logging.getLogger("SFLN-Server")
        self.logger.setLevel(log_level)
        logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)s] %(message)s')

    async def start(self):
        self.logger.info(f"SFLN Professional Server starting...")
        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: SFLNServerProtocol(self), local_addr=('0.0.0.0', self.port)
        )
        async with websockets.serve(self.ws_handler, "0.0.0.0", self.ws_port):
            await asyncio.Future()

    async def ws_handler(self, websocket):
        node_id_bytes = None
        try:
            async for message in websocket:
                if isinstance(message, str):
                    msg = json.loads(message)
                    if msg.get("type") == "register":
                        node_id_str = msg.get("node_id")
                        node_id_bytes = uuid.UUID(node_id_str).bytes
                        self.ws_peers[node_id_bytes] = (websocket, node_id_str)
                        self.logger.info(f"Registered WS node {node_id_str}")
                        await websocket.send(json.dumps({"type": "reg_ack"}))
                elif isinstance(message, bytes):
                    # Format: [Magic(1)][Type(1)][TargetID(16)][Total(4)][Idx(4)][Payload]
                    if len(message) > 18 and message[0] == 0x53 and message[1] == 0x01:
                        target_id_bytes = message[2:18]
                        source_id_bytes = node_id_bytes or b'\x00'*16
                        # Wrap for relay: [Magic(1)][Relay(1)][SourceID(16)][Total(4)][Idx(4)][Payload]
                        relay_packet = bytearray([0x53, 0x02]) + source_id_bytes + message[18:]
                        await self.relay_data(target_id_bytes, relay_packet)
        finally:
            if node_id_bytes in self.ws_peers: del self.ws_peers[node_id_bytes]

    async def relay_data(self, target_id, packet):
        if target_id in self.udp_peers:
            self.transport.sendto(packet, self.udp_peers[target_id])
        elif target_id in self.ws_peers:
            await self.ws_peers[target_id][0].send(packet)

class SFLNServerProtocol(asyncio.DatagramProtocol):
    def __init__(self, server):
        self.server = server
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if len(data) > 18 and data[0] == 0x53 and data[1] == 0x01:
            target_id = data[2:18]
            # Simple relay (SourceID not easily known from UDP without session)
            relay_packet = bytearray([0x53, 0x02]) + b'\x00'*16 + data[18:]
            asyncio.create_task(self.server.relay_data(target_id, relay_packet))
        elif data.startswith(b'{'):
            msg = json.loads(data.decode())
            if msg.get("type") == "register":
                nid = uuid.UUID(msg.get("node_id")).bytes
                self.server.udp_peers[nid] = addr
                self.transport.sendto(json.dumps({"type": "reg_ack"}).encode(), addr)

if __name__ == "__main__":
    asyncio.run(SFLNServer().start())
