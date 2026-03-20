import asyncio
import socket
import time
import logging
import uuid
import struct

class SFLNProtocol:
    """
    SFLN-P v2: High-Speed UDP-based Protocol.
    Optimized v2.2 with transfer progress reporting.
    """
    CHUNK_SIZE = 1024
    PARALLEL_STREAMS = 20
    MAGIC = 0x53

    def __init__(self, host='0.0.0.0', port=0, node_id=None):
        self.host = host
        self.port = port
        self.node_id = node_id or str(uuid.uuid4())
        self.node_id_bytes = uuid.UUID(self.node_id).bytes
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024*64)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024*64)
        except: pass
        if port != 0: self.sock.bind((host, port))
        self.logger = logging.getLogger("SFLN-P")

    def _create_header(self, ptype, target_id_bytes, seq, total):
        ver_type = (0x2 << 4) | (ptype & 0xF)
        return struct.pack("!BB16s16sII", self.MAGIC, ver_type, self.node_id_bytes, target_id_bytes, seq, total)

    async def send_data(self, encrypted_chunks, target_peer_id, target_address, progress_callback=None):
        """Send chunks with reporting."""
        start_time = time.time()
        target_id_bytes = uuid.UUID(target_peer_id).bytes
        total_chunks = len(encrypted_chunks)
        sent_chunks = 0
        total_bytes = 0

        loop = asyncio.get_event_loop()

        async def worker(queue):
            nonlocal sent_chunks, total_bytes
            while not queue.empty():
                idx, chunk = await queue.get()
                try:
                    header = self._create_header(0, target_id_bytes, idx, total_chunks)
                    packet = header + chunk
                    await loop.sock_sendto(self.sock, memoryview(packet), target_address)
                    sent_chunks += 1
                    total_bytes += len(packet)
                    if progress_callback and sent_chunks % 100 == 0:
                        progress_callback(sent_chunks, total_chunks)
                except Exception as e:
                    self.logger.error(f"Transport error: {e}")
                finally:
                    queue.task_done()

        queue = asyncio.Queue()
        for i, chunk in enumerate(encrypted_chunks):
            queue.put_nowait((i, chunk))

        tasks = [asyncio.create_task(worker(queue)) for _ in range(self.PARALLEL_STREAMS)]
        await asyncio.gather(*tasks)
        if progress_callback: progress_callback(total_chunks, total_chunks)

        duration = time.time() - start_time
        throughput = (total_bytes / duration) / (1024 * 1024) if duration > 0 else 0
        self.logger.info(f"SFLN-P: Sent {total_bytes} bytes in {duration:.2f}s ({throughput:.2f} MB/s)")

    async def receive_data(self, expected_chunks_count, progress_callback=None):
        received_chunks = {}
        loop = asyncio.get_event_loop()
        while len(received_chunks) < expected_chunks_count:
            data, addr = await loop.sock_recvfrom(self.sock, 2048)
            if len(data) < 42 or data[0] != self.MAGIC: continue
            _, ver_type, src_id, tgt_id, seq, total = struct.unpack("!BB16s16sII", data[:42])
            received_chunks[seq] = data[42:]
            if progress_callback and len(received_chunks) % 100 == 0:
                progress_callback(len(received_chunks), expected_chunks_count)
        return [received_chunks[i] for i in sorted(received_chunks.keys())]

class SFLNRouter:
    def __init__(self):
        self.routes_metrics = {}
        self.path_types = ["direct", "turn", "backbone"]
    def get_best_route(self, peer): return "backbone"
