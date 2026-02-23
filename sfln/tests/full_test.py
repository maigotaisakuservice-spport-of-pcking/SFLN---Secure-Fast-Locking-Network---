import asyncio
import time
import sys
import os

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sfln.core import SFLNEngine

async def test_encryption_performance():
    print("--- Testing 12,000-digit Encryption Performance ---")
    engine = SFLNEngine()
    data = os.urandom(1024 * 1024 * 10) # 10MB test data

    start = time.time()
    chunks = engine.crypto.encrypt_data(data)
    encrypt_time = time.time() - start
    print(f"Encrypted 10MB in {encrypt_time:.4f}s")

    start = time.time()
    decrypted = engine.crypto.decrypt_chunks(chunks)
    decrypt_time = time.time() - start
    print(f"Decrypted 10MB in {decrypt_time:.4f}s")

    assert data == decrypted
    print("Encryption integrity check passed.")

async def test_mesh_and_auth():
    print("\n--- Testing Mesh Discovery and Context Auth ---")
    engine_a = SFLNEngine(node_id="Node-A")
    engine_b = SFLNEngine(node_id="Node-B")

    context_a = engine_a.auth.get_current_context()
    valid, reason = engine_b.mesh.auth.verify_context(context_a)
    print(f"Context Auth verification result: {valid} ({reason})")
    assert valid

async def test_exclusions():
    print("\n--- Testing Exclusion Logic ---")
    engine = SFLNEngine()
    engine.excluded_apps.add("chrome.exe")
    engine.excluded_sites.add("google.com")

    assert engine.should_bypass(app_name="chrome.exe") == True
    assert engine.should_bypass(target_site="https://google.com/search") == True
    assert engine.should_bypass(app_name="other.exe", target_site="example.com") == False
    print("Exclusion logic verified.")

async def main():
    await test_encryption_performance()
    await test_mesh_and_auth()
    await test_exclusions()
    print("\nAll tests passed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
