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
        os.system('cls' if os.name == 'nt' else 'clear')
        print("┌" + "─"*70 + "┐")
        print(f"│ SFLN Backbone Relay Server - v1.0.0 {' '*31} │")
        print(f"│ Author: TekipakiPC {' '*49} │")
        print("├" + "─"*70 + "┤")
        print(f"│ UDP: 0.0.0.0:{self.port} {' '*49} │")
        print(f"│ WebSocket: 0.0.0.0:{self.ws_port} {' '*41} │")
        print(f"│ Status: [LISTENING] Ready for Mesh Connections {' '*19} │")
        print("└" + "─"*70 + "┘")

        self.logger.info(f"SFLN Professional Server starting...")

        loop = asyncio.get_running_loop()
        try:
            self.transport, _ = await loop.create_datagram_endpoint(
                lambda: SFLNServerProtocol(self), local_addr=('0.0.0.0', self.port)
            )
        except Exception as e:
            self.logger.error(f"Failed to start UDP server: {e}")

        # Increased ping/timeout for Cloudflare Tunnel stability
        try:
            async with websockets.serve(
                self.ws_handler,
                "0.0.0.0",
                self.ws_port,
                ping_interval=10,
                ping_timeout=10,
                process_request=self.process_request # Optional logging
            ) as ws_server:
                self.logger.info("WebSocket Server is running.")
                await asyncio.Future() # Run forever
        except Exception as e:
            self.logger.error(f"WebSocket Server failed: {e}")

    async def process_request(self, connection, request):
        self.logger.debug(f"WS Request from {request.headers.get('User-Agent')}")
        return None

    async def ws_handler(self, websocket):
        node_id_bytes = None
        addr = websocket.remote_address
        self.logger.info(f"New WS connection from {addr}")

        try:
            async for message in websocket:
                if isinstance(message, str):
                    try:
                        msg = json.loads(message)
                        if msg.get("type") == "register":
                            node_id_str = msg.get("node_id")
                            node_id_bytes = uuid.UUID(node_id_str).bytes
                            self.ws_peers[node_id_bytes] = (websocket, node_id_str)
                            self.logger.info(f"Registered WS node {node_id_str} ({addr})")
                            await websocket.send(json.dumps({"type": "reg_ack"}))
                    except Exception as e:
                        self.logger.error(f"WS JSON error from {addr}: {e}")

                elif isinstance(message, bytes):
                    # Format: [Magic(1)][Type(1)][TargetID(16)][Total(4)][Idx(4)][Payload]
                    if len(message) > 18 and message[0] == 0x53 and message[1] == 0x01:
                        target_id_bytes = message[2:18]
                        source_id_bytes = node_id_bytes or b'\x00'*16
                        # Wrap for relay: [Magic(1)][Relay(1)][SourceID(16)][Total(4)][Idx(4)][Payload]
                        relay_packet = bytearray([0x53, 0x02]) + source_id_bytes + message[18:]
                        await self.relay_data(target_id_bytes, relay_packet)
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"WS connection closed for {addr}")
        except Exception as e:
            self.logger.error(f"WS error for {addr}: {e}")
        finally:
            if node_id_bytes and node_id_bytes in self.ws_peers:
                del self.ws_peers[node_id_bytes]
                self.logger.info(f"Unregistered WS node {node_id_bytes.hex()}")

    async def relay_data(self, target_id, packet):
        # Relay to UDP
        if target_id in self.udp_peers:
            self.transport.sendto(packet, self.udp_peers[target_id])

        # Relay to WS
        if target_id in self.ws_peers:
            ws, _ = self.ws_peers[target_id]
            try:
                await ws.send(packet)
            except Exception as e:
                self.logger.error(f"WS Relay send failed: {e}")

class SFLNServerProtocol(asyncio.DatagramProtocol):
    def __init__(self, server):
        self.server = server
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if len(data) > 18 and data[0] == 0x53 and data[1] == 0x01:
            target_id = data[2:18]
            relay_packet = bytearray([0x53, 0x02]) + b'\x00'*16 + data[18:]
            asyncio.create_task(self.server.relay_data(target_id, relay_packet))
        elif data.startswith(b'{'):
            try:
                msg = json.loads(data.decode())
                if msg.get("type") == "register":
                    nid = uuid.UUID(msg.get("node_id")).bytes
                    self.server.udp_peers[nid] = addr
                    self.server.logger.info(f"Registered UDP node {msg.get('node_id')} at {addr}")
                    self.transport.sendto(json.dumps({"type": "reg_ack"}).encode(), addr)
            except: pass

if __name__ == "__main__":
    try:
        asyncio.run(SFLNServer().start())
    except KeyboardInterrupt:
        pass
