import asyncio
import logging
import sys
import os
import json
import uuid
import websockets
import time
from datetime import datetime

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sfln.core import SFLNEngine

class SFLNServer:
    def __init__(self, port=9000, ws_port=9001, log_level=logging.INFO):
        self.port = port
        self.ws_port = ws_port
        self.engine = SFLNEngine()
        self.udp_peers = {} # {node_id_bytes: addr}
        self.ws_peers = {}  # {node_id_bytes: (websocket, node_id_str, start_time)}
        self.logger = logging.getLogger("SFLN-Server")
        self.logger.setLevel(log_level)
        self.total_bytes_relayed = 0
        self.start_time = time.time()
        logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)s] %(message)s')

    async def update_dashboard(self):
        """Enterprise Dashboard (CUI)."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            uptime = time.time() - self.start_time
            throughput = self.total_bytes_relayed / uptime if uptime > 0 else 0

            print("┌" + "─"*78 + "┐")
            print(f"│ SFLN Enterprise Backbone - v2.0 (SFLN-P Standard) {' '*24} │")
            print(f"│ Current Time: {now} {' '*38} │")
            print(f"│ Uptime: {uptime/3600:.2f} hrs | Status: [LISTENING] {' '*32} │")
            print("├" + "─"*78 + "┤")
            print(f"│ STATS: Total Relayed: {self.total_bytes_relayed/1024/1024:.2f} MB {' '*35} │")
            print(f"│        Avg Throughput: {throughput/1024/1024*8:.2f} Mbps {' '*36} │")
            print(f"│        Connected Peers: {len(self.udp_peers) + len(self.ws_peers)} (UDP: {len(self.udp_peers)}, WS: {len(self.ws_peers)}) {' '*18} │")
            print("├" + "─"*30 + " CONNECTED DEVICES " + "─"*29 + "┤")

            count = 0
            for nid_bytes, (ws, nid_str, start) in list(self.ws_peers.items()):
                if count >= 10: break
                peer_uptime = time.time() - start
                print(f"│ [WS]  {nid_str[:12]}... | {ws.remote_address[0]:15} | Uptime: {peer_uptime:6.0f}s {' '*13} │")
                count += 1

            for nid_bytes, addr in list(self.udp_peers.items()):
                if count >= 15: break
                nid_str = str(uuid.UUID(bytes=nid_bytes))
                print(f"│ [UDP] {nid_str[:12]}... | {addr[0]:15} | Protocol: SFLN-P-v2 {' '*18} │")
                count += 1

            if count == 0:
                print(f"│ {' '*32} No active peers. {' '*29} │")

            print("└" + "─"*78 + "┘")
            print("  Log: Press Ctrl+C to stop.")
            await asyncio.sleep(2)

    async def start(self):
        self.logger.info(f"SFLN Professional Server starting...")

        # Start dashboard task
        asyncio.create_task(self.update_dashboard())

        loop = asyncio.get_running_loop()
        try:
            self.transport, _ = await loop.create_datagram_endpoint(
                lambda: SFLNServerProtocol(self), local_addr=('0.0.0.0', self.port)
            )
        except Exception as e:
            self.logger.error(f"Failed to start UDP server: {e}")

        try:
            async with websockets.serve(
                self.ws_handler,
                "0.0.0.0",
                self.ws_port,
                ping_interval=10,
                ping_timeout=10,
            ) as ws_server:
                self.logger.info("WebSocket Server is running.")
                await asyncio.Future() # Run forever
        except Exception as e:
            self.logger.error(f"WebSocket Server failed: {e}")

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
                            self.ws_peers[node_id_bytes] = (websocket, node_id_str, time.time())
                            self.logger.info(f"Registered WS node {node_id_str} ({addr})")
                            await websocket.send(json.dumps({"type": "reg_ack"}))
                    except Exception as e:
                        self.logger.error(f"WS JSON error from {addr}: {e}")

                elif isinstance(message, bytes):
                    # SFLN-P v2 Format: [Magic(1)][Ver/Type(1)][SrcID(16)][TargetID(16)][Seq(4)][Total(4)][Payload...]
                    if len(message) > 42 and message[0] == 0x53:
                        target_id_bytes = message[18:34]
                        self.total_bytes_relayed += len(message)
                        await self.relay_data(target_id_bytes, message)
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
            ws, _, _ = self.ws_peers[target_id]
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
        # SFLN-P v2 Data Packet (Magic=0x53)
        if len(data) > 42 and data[0] == 0x53:
            target_id = data[18:34]
            self.server.total_bytes_relayed += len(data)
            asyncio.create_task(self.server.relay_data(target_id, data))
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
