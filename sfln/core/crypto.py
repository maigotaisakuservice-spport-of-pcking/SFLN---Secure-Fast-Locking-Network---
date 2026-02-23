import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

class SFLNCrypto:
    """
    SFLN Core Encryption Module (High-Performance version using AES-GCM)
    Implements 12,000-digit (approx 40,000-bit) key handling and 1KB chunk splitting.
    """
    KEY_DIGITS = 12000
    KEY_BITS = 40000  # Approx 12000 digits
    CHUNK_SIZE = 1024 # 1KB
    KEY_EMBED_SIZE = 32 # Size of the per-chunk key seed embedded

    def __init__(self, master_key: bytes = None):
        if master_key:
            self.master_key = master_key
        else:
            self.master_key = os.urandom(self.KEY_BITS // 8)

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

    def encrypt_data(self, data: bytes):
        """Encrypts data into 1KB chunks with embedded seeds."""
        encrypted_chunks = []
        for i in range(0, len(data), self.CHUNK_SIZE):
            chunk = data[i:i + self.CHUNK_SIZE]
            idx = i // self.CHUNK_SIZE
            chunk_seed = os.urandom(self.KEY_EMBED_SIZE)
            key = self._derive_chunk_key(idx, chunk_seed)

            aesgcm = AESGCM(key)
            nonce = os.urandom(12)
            encrypted_payload = aesgcm.encrypt(nonce, chunk, None)

            # Format: [Nonce(12)][Seed(32)][EncryptedData+Tag]
            final_chunk = nonce + chunk_seed + encrypted_payload
            encrypted_chunks.append(final_chunk)
        return encrypted_chunks

    def decrypt_chunks(self, chunks: list):
        """Decrypts and reassembles chunks."""
        decrypted_data = bytearray()
        for i, chunk in enumerate(chunks):
            nonce = chunk[:12]
            chunk_seed = chunk[12:12+self.KEY_EMBED_SIZE]
            encrypted_payload = chunk[12+self.KEY_EMBED_SIZE:]

            key = self._derive_chunk_key(i, chunk_seed)
            aesgcm = AESGCM(key)

            try:
                decrypted_chunk = aesgcm.decrypt(nonce, encrypted_payload, None)
                decrypted_data.extend(decrypted_chunk)
            except Exception as e:
                raise ValueError(f"Decryption failed at chunk {i}: {e}")
        return bytes(decrypted_data)

if __name__ == "__main__":
    crypto = SFLNCrypto()
    test_data = b"SFLN AES-GCM High-Performance Test " * 50
    chunks = crypto.encrypt_data(test_data)
    decrypted = crypto.decrypt_chunks(chunks)
    assert decrypted == test_data
    print(f"Success. Master Key: {len(crypto.master_key)} bytes.")
