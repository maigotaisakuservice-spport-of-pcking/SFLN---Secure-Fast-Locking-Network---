import asyncio
import logging
import sys
import os
import json
import uuid
import websockets
import ssl

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sfln.core import SFLNEngine

class SFLNServer:
    """
    SFLN High-Performance Backbone Server.
    Supports UDP (Native Clients) and WebSocket (Web Clients).
    """
    def __init__(self, port=9000, ws_port=9001, log_level=logging.INFO):
        self.port = port
        self.ws_port = ws_port
        self.engine = SFLNEngine()
        # peers mapping: {node_id_bytes: {'type': 'udp', 'addr': addr} OR {'type': 'ws', 'ws': websocket}}
        self.peers = {}
        self.logger = logging.getLogger("SFLN-Server")
        self.logger.setLevel(log_level)
        logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)s] %(message)s')

    async def start(self):
        self.logger.info(f"SFLN Professional Server starting. UDP:{self.port}, WS:{self.ws_port}")
        loop = asyncio.get_running_loop()

        # Start UDP Server
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: SFLNServerProtocol(self),
            local_addr=('0.0.0.0', self.port)
        )

        # Setup SSL for Secure WebSockets if cert files exist
        ssl_context = None
        cert_path = "cert.pem"
        key_path = "key.pem"
        if os.path.exists(cert_path) and os.path.exists(key_path):
            self.logger.info("SSL Certificate found. Enabling WSS (Secure WebSockets).")
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)

        # Start WebSocket Server
        async with websockets.serve(self.ws_handler, "0.0.0.0", self.ws_port, ssl=ssl_context):
            self.logger.info(f"WebSocket Server listening on port {self.ws_port} ({'WSS' if ssl_context else 'WS'})")
            await asyncio.Future()  # run forever

    async def ws_handler(self, websocket):
        node_id_bytes = None
        try:
            async for message in websocket:
                if isinstance(message, str):
                    msg = json.loads(message)
                    mtype = msg.get("type")

                    if mtype == "register":
                        node_id_str = msg.get("node_id")
                        node_id_bytes = uuid.UUID(node_id_str).bytes
                        self.peers[node_id_bytes] = {'type': 'ws', 'ws': websocket}
                        self.logger.info(f"Registered WS node {node_id_str}")
                        await websocket.send(json.dumps({"type": "reg_ack"}))

                    elif mtype == "get_peers":
                        peers_list = [str(uuid.UUID(bytes=nid)) for nid in self.peers.keys()]
                        await websocket.send(json.dumps({"type": "peers", "list": peers_list}))

                    elif mtype == "relay":
                        target_id_str = msg.get("target_id")
                        payload_hex = msg.get("payload") # Hex encoded binary for JSON compatibility
                        target_id_bytes = uuid.UUID(target_id_str).bytes
                        await self.relay_message(target_id_bytes, bytes.fromhex(payload_hex), source_id_bytes=node_id_bytes)

                elif isinstance(message, bytes):
                    # Binary relay over WS: [Magic: 'S' (1b)][Type: 0x01 (1b)][TargetID (16b)][Payload]
                    if message[0] == 0x53 and len(message) > 18:
                        if message[1] == 0x01:
                            target_id = message[2:18]
                            await self.relay_message(target_id, message[18:], source_id_bytes=node_id_bytes)

        except websockets.ConnectionClosed:
            pass
        finally:
            if node_id_bytes and node_id_bytes in self.peers:
                if self.peers[node_id_bytes].get('ws') == websocket:
                    del self.peers[node_id_bytes]
                    self.logger.info(f"WS node disconnected: {uuid.UUID(bytes=node_id_bytes)}")

    async def relay_message(self, target_id_bytes, payload, source_id_bytes=None):
        if target_id_bytes in self.peers:
            target = self.peers[target_id_bytes]
            if target['type'] == 'udp':
                # Wrap for UDP client: [Magic][Type: 0x02 (Relayed)][Payload]
                relay_packet = bytearray([0x53, 0x02]) + payload
                self.transport.sendto(relay_packet, target['addr'])
            elif target['type'] == 'ws':
                # Wrap for WS client: [Magic][Type: 0x02 (Relayed)][Payload]
                relay_packet = bytearray([0x53, 0x02]) + payload
                await target['ws'].send(relay_packet)

class SFLNServerProtocol(asyncio.DatagramProtocol):
    def __init__(self, server):
        self.server = server
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if not data: return

        # High-Speed Binary Relay Path
        if data[0] == 0x53 and len(data) > 18:
            msg_type = data[1]
            if msg_type == 0x01: # RELAY
                target_id = data[2:18]
                asyncio.create_task(self.server.relay_message(target_id, data[18:]))
                return

        # Control Channel (JSON)
        try:
            if data.startswith(b'{'):
                msg = json.loads(data.decode())
                mtype = msg.get("type")

                if mtype == "register":
                    node_id_str = msg.get("node_id")
                    node_id_bytes = uuid.UUID(node_id_str).bytes
                    self.server.peers[node_id_bytes] = {'type': 'udp', 'addr': addr}
                    self.server.logger.info(f"Registered UDP node {node_id_str} at {addr}")
                    self.transport.sendto(json.dumps({"type": "reg_ack"}).encode(), addr)

                elif mtype == "get_peers":
                    peers_list = [str(uuid.UUID(bytes=nid)) for nid in self.server.peers.keys()]
                    self.transport.sendto(json.dumps({"type": "peers", "list": peers_list}).encode(), addr)
        except Exception as e:
            self.server.logger.error(f"Error handling UDP control packet: {e}")

if __name__ == "__main__":
    server = SFLNServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass
