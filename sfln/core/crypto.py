import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
import multiprocessing

class SFLNCrypto:
    """
    SFLN Core Encryption Module (High-Performance version using AES-GCM)
    Implements 12,000-digit (approx 40,000-bit) key handling and 1KB chunk splitting.
    Reference implementation for SFLN-P v2.
    """
    KEY_DIGITS = 12000
    KEY_BITS = 40000  # Approx 12000 digits
    CHUNK_SIZE = 1024 # 1KB
    KEY_EMBED_SIZE = 32 # Size of the per-chunk key seed embedded

    def __init__(self, master_key: bytes = None):
        if master_key:
            self.master_key = master_key
        else:
            self.master_key = self.generate_master_key()
        self.session_keys = {} # {peer_id: shared_secret}

    @classmethod
    def generate_master_key(cls):
        return os.urandom(cls.KEY_BITS // 8)

    def _derive_chunk_key(self, chunk_index: int, chunk_seed: bytes):
        """Derive a 256-bit AES key for a chunk using HKDF."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=chunk_seed,
            info=str(chunk_index).encode(),
        )
        return hkdf.derive(self.master_key)

    def encrypt_chunk(self, args):
        """Helper for parallel encryption."""
        chunk, idx = args
        chunk_seed = os.urandom(self.KEY_EMBED_SIZE)
        key = self._derive_chunk_key(idx, chunk_seed)

        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        encrypted_payload = aesgcm.encrypt(nonce, chunk, None)

        # Format: [Nonce(12)][Seed(32)][EncryptedData+Tag]
        return nonce + chunk_seed + encrypted_payload

    def decrypt_chunk_worker(self, args):
        """Helper for parallel decryption."""
        chunk, idx = args
        nonce = chunk[:12]
        chunk_seed = chunk[12:12+self.KEY_EMBED_SIZE]
        encrypted_payload = chunk[12+self.KEY_EMBED_SIZE:]

        key = self._derive_chunk_key(idx, chunk_seed)
        aesgcm = AESGCM(key)

        try:
            return aesgcm.decrypt(nonce, encrypted_payload, None)
        except Exception as e:
            return None

    def encrypt_data(self, data: bytes, parallel=True):
        """Encrypts data into 1KB chunks. Uses pool for 1GB/s target (Principle C)."""
        chunks = [data[i:i + self.CHUNK_SIZE] for i in range(0, len(data), self.CHUNK_SIZE)]

        if not parallel or len(chunks) < 10:
            return [self.encrypt_chunk((c, i)) for i, c in enumerate(chunks)]

        with multiprocessing.Pool() as pool:
            return pool.map(self.encrypt_chunk, [(c, i) for i, c in enumerate(chunks)])

    def decrypt_chunks(self, chunks: list, parallel=True):
        """Decrypts and reassembles chunks."""
        if not parallel or len(chunks) < 10:
            results = [self.decrypt_chunk_worker((c, i)) for i, c in enumerate(chunks)]
        else:
            with multiprocessing.Pool() as pool:
                results = pool.map(self.decrypt_chunk_worker, [(c, i) for i, c in enumerate(chunks)])

        decrypted_data = bytearray()
        for i, res in enumerate(results):
            if res is None:
                raise ValueError(f"Decryption failed at chunk {i}")
            decrypted_data.extend(res)
        return bytes(decrypted_data)

if __name__ == "__main__":
    crypto = SFLNCrypto()
    test_data = b"SFLN AES-GCM High-Performance Test " * 1000
    print(f"Encrypting {len(test_data)} bytes...")
    chunks = crypto.encrypt_data(test_data)
    decrypted = crypto.decrypt_chunks(chunks)
    assert decrypted == test_data
    print(f"Success. Master Key: {len(crypto.master_key)} bytes. Chunks: {len(chunks)}")
