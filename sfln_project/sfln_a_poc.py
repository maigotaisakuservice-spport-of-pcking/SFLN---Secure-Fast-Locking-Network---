import os
import hashlib
import uuid
import random
import math
import json

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
except ImportError:
    print("Error: PyCryptodome is not installed. Please run 'pip install pycryptodome'")
    exit(1)

# Constants from the specification
CHUNK_SIZE = 1024
KEY_SIZE = 32  # 256 bits for AES Master Key
TAG_SIZE = 16  # 128 bits for GCM Authentication Tag
NONCE_SIZE = 16 # 128 bits for GCM Nonce

class SflnAProcessor:
    """
    Implements the SFLN-A protocol for encrypting/splitting and
    reassembling/decrypting data.
    """

    def _create_chunk(self, file_id, total_chunks, chunk_index, is_key_chunk, payload):
        """Helper to construct a single chunk with its header."""
        payload_hash = hashlib.sha256(payload).digest()

        # Header construction
        header = b''
        header += file_id.bytes
        header += total_chunks.to_bytes(4, 'big')
        header += chunk_index.to_bytes(4, 'big')
        header += (1 if is_key_chunk else 0).to_bytes(1, 'big')
        header += payload_hash

        return header + payload

    def encrypt_and_split(self, data: bytes):
        """
        Encrypts the data and splits it into SFLN-A chunks.

        Args:
            data: The raw data to process.

        Returns:
            A list of bytes objects, where each is a complete SFLN-A chunk.
        """
        master_key = get_random_bytes(KEY_SIZE)
        file_id = uuid.uuid4()

        cipher = AES.new(master_key, AES.MODE_GCM)
        encrypted_payload, auth_tag = cipher.encrypt_and_digest(data)
        nonce = cipher.nonce

        total_chunks = math.ceil(len(encrypted_payload) / CHUNK_SIZE)
        if total_chunks == 0:
             total_chunks = 1
        key_chunk_index = random.randint(0, total_chunks - 1)

        chunks = []
        for i in range(total_chunks):
            is_key_chunk = (i == key_chunk_index)

            start = i * CHUNK_SIZE
            end = start + CHUNK_SIZE
            payload_segment = encrypted_payload[start:end]

            if is_key_chunk:
                final_payload = master_key + nonce + auth_tag + payload_segment
            else:
                final_payload = payload_segment

            chunk = self._create_chunk(file_id, total_chunks, i, is_key_chunk, final_payload)
            chunks.append(chunk)

        return chunks

    def reassemble_and_decrypt(self, chunks: list):
        """
        Reassembles SFLN-A chunks and decrypts the data.

        Args:
            chunks: A list of SFLN-A chunk bytes.

        Returns:
            The original decrypted data, or None if decryption fails.
        """
        if not chunks:
            return b''

        parsed_chunks = {}
        file_id = None
        for chunk in chunks:
            header = chunk[:57]
            payload = chunk[57:]

            payload_hash = hashlib.sha256(payload).digest()
            if payload_hash != header[25:57]:
                print(f"[!] Error: Chunk hash mismatch!")
                return None

            if file_id is None:
                file_id = uuid.UUID(bytes=header[0:16])

            chunk_index = int.from_bytes(header[20:24], 'big')
            parsed_chunks[chunk_index] = {
                "is_key_chunk": bool(header[24]),
                "payload": payload
            }

        master_key, nonce, auth_tag = None, None, None
        total_chunks = len(parsed_chunks)
        encrypted_payload_segments = [b''] * total_chunks

        for i in range(total_chunks):
            chunk_data = parsed_chunks[i]
            if chunk_data["is_key_chunk"]:
                key_payload = chunk_data["payload"]
                master_key = key_payload[:KEY_SIZE]
                nonce = key_payload[KEY_SIZE:KEY_SIZE+NONCE_SIZE]
                auth_tag = key_payload[KEY_SIZE+NONCE_SIZE:KEY_SIZE+NONCE_SIZE+TAG_SIZE]
                encrypted_payload_segments[i] = key_payload[KEY_SIZE+NONCE_SIZE+TAG_SIZE:]
            else:
                encrypted_payload_segments[i] = chunk_data["payload"]

        if not all([master_key, nonce, auth_tag]):
            return None

        reassembled_payload = b"".join(encrypted_payload_segments)
        cipher = AES.new(master_key, AES.MODE_GCM, nonce=nonce)
        try:
            decrypted_data = cipher.decrypt_and_verify(reassembled_payload, auth_tag)
            return decrypted_data
        except ValueError:
            return None

def generate_js_test_data():
    """Generates a JSON file with test data for the JS library."""
    print("\n--- Generating Test Data for JS ---")
    processor = SflnAProcessor()
    original_data_str = "This is the secret message for the JavaScript test."
    original_data_bytes = original_data_str.encode('utf-8')

    sfln_chunks = processor.encrypt_and_split(original_data_bytes)

    # Convert each chunk to a list of bytes (integers) for JSON serialization
    chunks_as_lists = [list(chunk) for chunk in sfln_chunks]

    test_data = {
        "original_message": original_data_str,
        "chunks": chunks_as_lists
    }

    output_filename = "sfln_project/js_test_data.json"
    with open(output_filename, 'w') as f:
        json.dump(test_data, f, indent=2)

    print(f"[SUCCESS] Test data written to {output_filename}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--export-js':
        generate_js_test_data()
    else:
        print("--- SFLN-A Protocol PoC ---")
        processor = SflnAProcessor()

        # Run standard test
        original_data = b"This is a secret message that is longer than one chunk." * 20
        print(f"\n[1] Original Data Size: {len(original_data)} bytes")
        sfln_chunks = processor.encrypt_and_split(original_data)
        random.shuffle(sfln_chunks)
        decrypted_data = processor.reassemble_and_decrypt(sfln_chunks)

        assert original_data == decrypted_data
        print("[SUCCESS] Main test passed.")

        # Test with empty data
        original_empty = b""
        empty_chunks = processor.encrypt_and_split(original_empty)
        decrypted_empty = processor.reassemble_and_decrypt(empty_chunks)
        assert original_empty == decrypted_empty
        print("[SUCCESS] Empty data test passed.")

        print("\n--- PoC Completed ---")
        print("Hint: Run with '--export-js' to generate data for the web demo.")
