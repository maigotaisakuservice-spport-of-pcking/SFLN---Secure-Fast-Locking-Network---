import asyncio
import sys
import os
import logging

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sfln.core import SFLNEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Chaos-Test")

async def test_ai_routing_decisions():
    logger.info("--- Testing AI Dynamic Routing Decisions ---")
    engine = SFLNEngine()
    peer_id = "target-node-99"

    # Path A: Stable but slow (Latency 50ms, Loss 0%)
    for _ in range(10):
        engine.router.update_metrics(peer_id, "direct", latency=50, packet_loss=0.0)

    # Path B: Fast but unreliable (Latency 10ms, Loss 10%)
    for _ in range(10):
        engine.router.update_metrics(peer_id, "backbone", latency=10, packet_loss=0.1)

    # Calculate score for Path A: (50*0.5) + (0*5000) = 25
    # Calculate score for Path B: (10*0.5) + (0.1*5000) = 5 + 500 = 505
    # Path A should be chosen even though it's slower because it's reliable.

    best = engine.router.get_best_route(peer_id)
    logger.info(f"Stable but slow route vs Fast but unreliable route.")
    logger.info(f"Selected route: {best}")
    assert best == "direct"

    # Now simulate Path B improving (Loss 0%)
    # We need to clear the history of 0.1 loss by adding more 0.0 loss entries
    for _ in range(100):
        engine.router.update_metrics(peer_id, "backbone", latency=10, packet_loss=0.0)

    best = engine.router.get_best_route(peer_id)
    logger.info(f"After Path B becomes reliable for 100 samples, selected route: {best}")
    # Now the average loss for Path B is almost 0. Score for B ~ 5, Score for A = 25.
    assert best == "backbone"
    print("✅ AI Routing decision test passed.")

async def test_context_rejection():
    logger.info("\n--- Testing Context-Based Rejection ---")
    engine = SFLNEngine()

    # Peer with stale timestamp (potential replay attack)
    bad_context = {
        "device_id": "malicious-node",
        "timestamp": 0, # Ancient
        "os": "Unknown"
    }

    valid, reason = engine.auth.verify_context(bad_context)
    logger.info(f"Bad context verification: {valid} ({reason})")
    assert valid == False
    print("✅ Context rejection verified.")

async def main():
    await test_ai_routing_decisions()
    await test_context_rejection()

if __name__ == "__main__":
    asyncio.run(main())
