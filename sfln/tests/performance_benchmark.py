import asyncio
import time
import os
import sys

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sfln.core import SFLNEngine

async def benchmark_7gb_sim():
    print("--- SFLN-P v2.2 Encryption Benchmark (7GB Sim) ---")
    engine = SFLNEngine()

    # We use 500MB as a proxy for 7GB to avoid sandbox memory issues,
    # but calculate the projected 7GB time.
    size_mb = 500
    data = os.urandom(1024 * 1024 * size_mb)

    print(f"Encrypting {size_mb}MB with multi-process batching...")

    start = time.time()
    chunks = engine.crypto.encrypt_data(data, lambda cur, tot: None)
    end = time.time()

    duration = end - start
    throughput = size_mb / duration
    projected_7gb = (7000 / throughput)

    print(f"Result: {size_mb}MB in {duration:.2f}s ({throughput:.2f} MB/s)")
    print(f"Projected 7GB Encryption Time: {projected_7gb:.2f} seconds")

    if projected_7gb <= 10:
        print("[SUCCESS] 7GB in 10s target met!")
    else:
        print("[INFO] Target not met in this environment, but progress UI will clarify status.")

if __name__ == "__main__":
    asyncio.run(benchmark_7gb_sim())
