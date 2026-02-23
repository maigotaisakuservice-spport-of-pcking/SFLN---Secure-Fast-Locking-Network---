import time
import json
import hashlib
import socket
import platform

class ContextAuth:
    """
    SFLN Context-Based Authentication
    Uses device info, location (IP), and time for passwordless authentication.
    """
    def __init__(self, policy=None):
        self.policy = policy or {
            "allowed_countries": ["JP"], # Example
            "allowed_times": (0, 24),    # All day
            "trust_score_threshold": 70
        }

    @staticmethod
    def get_current_context():
        """Gather current device context."""
        context = {
            "device_id": hashlib.sha256(platform.node().encode()).hexdigest(),
            "os": platform.system(),
            "timestamp": time.time(),
            "local_ip": socket.gethostbyname(socket.gethostname()),
            # In a real app, we would add more like GeoIP, SSID, etc.
        }
        return context

    def verify_context(self, peer_context):
        """Verify if the peer's context meets the security policy."""
        # Simple simulation of context-based verification
        if not peer_context:
            return False, "Missing context"

        # Check timestamp (anti-replay)
        if abs(time.time() - peer_context.get("timestamp", 0)) > 300: # 5 min window
            return False, "Context expired (Time drift?)"

        # In a real implementation, we would check more factors
        # and calculate a trust score.
        return True, "Context verified"

    def sign_context(self, context, private_key):
        """In a real implementation, sign the context with a private key."""
        # Simulation: just return the context (would be a JWS or similar)
        return context
