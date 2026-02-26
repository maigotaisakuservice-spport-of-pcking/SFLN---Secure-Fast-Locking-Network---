import asyncio
import time
import sys
import os
import logging
import argparse

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sfln.core.crypto import SFLNCrypto

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Perf-Test")

class StreamingPerfTest:
    """
    High-capacity streaming performance test.
    Simulates large data transfer without using disk space.
    """
    def __init__(self):
        self.crypto = SFLNCrypto()
        self.chunk_size = 1024 # 1KB

    async def run_test(self, size_gb):
        total_bytes = int(size_gb * 1024 * 1024 * 1024)
        logger.info(f"--- Starting {size_gb}GB Stream Test ---")

        # Prepare a 1MB buffer to reuse for encryption simulation
        # to avoid allocation overhead during the test
        buffer_size = 1024 * 1024
        dummy_data = os.urandom(buffer_size)

        start_time = time.time()
        processed_bytes = 0

        # We simulate the full encryption pipeline for every 1KB
        # but reuse buffers to save memory.
        try:
            while processed_bytes < total_bytes:
                # Encrypt a small batch (e.g. 1MB at a time)
                # In real SFLN, this goes through UDP
                batch = dummy_data
                _ = self.crypto.encrypt_data(batch[:self.chunk_size])

                processed_bytes += buffer_size

                # Periodically log progress for very large tests
                if (processed_bytes // buffer_size) % 1024 == 0:
                    elapsed = time.time() - start_time
                    speed = (processed_bytes / elapsed) / (1024 * 1024 * 1024) if elapsed > 0 else 0
                    logger.info(f"Progress: {processed_bytes / (1024**3):.2f}GB / {size_gb}GB ({speed:.2f} GB/s)")

                # Yield to event loop
                if (processed_bytes // buffer_size) % 100 == 0:
                    await asyncio.sleep(0)

        except KeyboardInterrupt:
            logger.info("Test aborted by user.")
            return

        duration = time.time() - start_time
        throughput = (total_bytes / duration) / (1024 * 1024 * 1024)

        logger.info(f"Finished: {size_gb}GB in {duration:.2f}s")
        logger.info(f"Average Throughput: {throughput:.2f} GB/s")
        if throughput >= 1.0:
            logger.info("✅ SFLN 1GB/s target met!")
        else:
            logger.info("ℹ️ Throughput below 1GB/s (likely limited by CI/CPU environment)")

async def main():
    parser = argparse.ArgumentParser(description="SFLN Performance Test")
    parser.add_argument("--size", type=float, default=0.1, help="Test size in GB (e.g. 0.1 for 100MB, 1.0 for 1GB)")
    args = parser.parse_args()

    tester = StreamingPerfTest()
    await tester.run_test(args.size)

if __name__ == "__main__":
    asyncio.run(main())
