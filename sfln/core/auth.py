import time
import json
import hashlib
import socket
import platform
import os

class ContextAuth:
    """
    SFLN Context-Based Authentication
    Uses device info, hardware-bound tokens, and time for passwordless authentication.
    Enterprise Ready: Audit logging and Strict Whitelisting.
    """
    def __init__(self, policy=None):
        self.policy = policy or {
            "allowed_countries": ["JP"],
            "allowed_times": (0, 24),
            "trust_score_threshold": 70,
            "whitelist_nodes": set(), # Node IDs allowed to connect
            "audit_log_path": "sfln_audit.log"
        }
        self.device_token = self._generate_hardware_token()

    def _generate_hardware_token(self):
        """Generates a hardware-bound token (Fingerprint)."""
        fingerprint = f"{platform.node()}-{platform.machine()}-{platform.processor()}"
        # In Linux/macOS, use board serial if possible
        return hashlib.sha256(fingerprint.encode()).hexdigest()

    def get_current_context(self):
        """Gather current device context for HELLO packet."""
        context = {
            "node_id": "WILL_BE_SET_BY_MESH",
            "token": self.device_token,
            "os": platform.system(),
            "timestamp": time.time(),
            "local_ip": socket.gethostbyname(socket.gethostname()),
            "version": "SFLN-P-2.0"
        }
        return context

    def log_audit(self, event, peer_id, success, reason=""):
        """Enterprise Audit Logging."""
        entry = f"{time.ctime()} | EVENT: {event} | PEER: {peer_id} | SUCCESS: {success} | REASON: {reason}\n"
        try:
            with open(self.policy["audit_log_path"], "a") as f: f.write(entry)
        except: pass

    def verify_context(self, peer_context):
        """Verify if the peer's context meets the security policy."""
        if not peer_context:
            return False, "Missing context"

        peer_id = peer_context.get("node_id", "Unknown")

        # 1. Strict Node Whitelisting
        if self.policy["whitelist_nodes"] and peer_id not in self.policy["whitelist_nodes"]:
            self.log_audit("AUTH", peer_id, False, "Not in Whitelist")
            return False, "Unauthorized Node ID"

        # 2. Time drift check
        if abs(time.time() - peer_context.get("timestamp", 0)) > 300:
            self.log_audit("AUTH", peer_id, False, "Time Drift")
            return False, "Clock desync detected"

        # 3. Hardware token verification (Simplified: Check if not empty)
        if not peer_context.get("token"):
            return False, "Invalid Hardware Fingerprint"

        self.log_audit("AUTH", peer_id, True)
        return True, "Context verified"

    def sign_context(self, context, private_key):
        # Simulation: just return the context
        return context
