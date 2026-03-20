import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import multiprocessing
import time

# Global for pool reuse
_crypto_pool = None

def _get_crypto_pool():
    global _crypto_pool
    if _crypto_pool is None:
        _crypto_pool = multiprocessing.Pool()
    return _crypto_pool

def encrypt_batch_task(args):
    """Process multiple chunks in one worker to minimize IPC overhead."""
    master_key, batch_chunks, start_idx = args
    results = []
    for i, chunk in enumerate(batch_chunks):
        idx = start_idx + i
        chunk_seed = os.urandom(32)
        hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=chunk_seed, info=str(idx).encode())
        key = hkdf.derive(master_key)

        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        encrypted_payload = aesgcm.encrypt(nonce, chunk, None)
        results.append(nonce + chunk_seed + encrypted_payload)
    return results

def decrypt_batch_task(args):
    """Process multiple chunks in one worker to minimize IPC overhead."""
    master_key, batch_chunks, start_idx = args
    results = []
    for i, chunk in enumerate(batch_chunks):
        idx = start_idx + i
        nonce = chunk[:12]
        chunk_seed = chunk[12:44]
        encrypted_payload = chunk[44:]

        hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=chunk_seed, info=str(idx).encode())
        key = hkdf.derive(master_key)
        aesgcm = AESGCM(key)
        try:
            results.append(aesgcm.decrypt(nonce, encrypted_payload, None))
        except:
            return None # Fail the whole batch
    return results

class SFLNCrypto:
    """
    SFLN Core Encryption Module (Optimized v2.2 - Batch Processing)
    Target: High throughput via minimized IPC overhead.
    """
    KEY_BITS = 40000
    CHUNK_SIZE = 1024
    BATCH_CHUNKS = 512 # 512KB per task

    def __init__(self, master_key: bytes = None):
        if master_key: self.master_key = master_key
        else: self.master_key = os.urandom(self.KEY_BITS // 8)

    def encrypt_data(self, data: bytes, progress_callback=None):
        total_size = len(data)
        chunks = [data[i:i + self.CHUNK_SIZE] for i in range(0, total_size, self.CHUNK_SIZE)]
        total_chunks = len(chunks)

        batches = []
        for i in range(0, total_chunks, self.BATCH_CHUNKS):
            batch = chunks[i : i + self.BATCH_CHUNKS]
            batches.append((self.master_key, batch, i))

        pool = _get_crypto_pool()
        all_encrypted = []

        for i, batch_result in enumerate(pool.imap(encrypt_batch_task, batches)):
            all_encrypted.extend(batch_result)
            if progress_callback:
                progress_callback(len(all_encrypted), total_chunks)

        return all_encrypted

    def decrypt_chunks(self, chunks: list, progress_callback=None):
        total_chunks = len(chunks)
        batches = []
        for i in range(0, total_chunks, self.BATCH_CHUNKS):
            batch = chunks[i : i + self.BATCH_CHUNKS]
            batches.append((self.master_key, batch, i))

        pool = _get_crypto_pool()
        all_decrypted = []

        for i, batch_result in enumerate(pool.imap(decrypt_batch_task, batches)):
            if batch_result is None:
                raise ValueError("Decryption failed in batch")
            all_decrypted.extend(batch_result)
            if progress_callback:
                progress_callback(len(all_decrypted), total_chunks)

        return b"".join(all_decrypted)

if __name__ == "__main__":
    crypto = SFLNCrypto()
    size_mb = 100
    data = os.urandom(1024 * 1024 * size_mb)
    print(f"Benchmarking {size_mb}MB encryption (Batch Mode)...")
    start = time.time()
    chunks = crypto.encrypt_data(data, lambda c, t: print(f"\rProgress: {c/t*100:.1f}%", end=""))
    end = time.time()
    print(f"\nEncrypted in {end-start:.4f}s ({size_mb/(end-start):.2f} MB/s)")
