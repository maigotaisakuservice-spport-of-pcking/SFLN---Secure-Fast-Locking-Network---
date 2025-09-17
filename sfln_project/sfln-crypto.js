/**
 * SFLN-Crypto.js
 * A JavaScript library to reassemble and decrypt SFLN-A protocol chunks.
 * This library is designed to be embedded in web pages.
 */

const sfln = {
    /**
     * Reassembles and decrypts a set of SFLN-A chunks.
     *
     * @param {Array<ArrayBuffer>} chunks An array of SFLN-A chunks, each as an ArrayBuffer.
     * @returns {Promise<Uint8Array>} A promise that resolves with the decrypted data as a Uint8Array.
     * @throws {Error} Throws an error if validation or decryption fails.
     */
    async reassembleAndDecrypt(chunks) {
        console.log("[sfln.js] Starting reassembly and decryption...");

        if (!chunks || chunks.length === 0) {
            console.log("[sfln.js] No chunks provided, returning empty data.");
            return new Uint8Array(0);
        }

        // --- Step 1: Parse and Verify All Chunks ---
        const parsedChunks = new Map();
        let fileId = null;
        let totalChunks = -1;

        for (const chunkBuffer of chunks) {
            const chunkView = new DataView(chunkBuffer);
            const payload = chunkBuffer.slice(57);

            // Verify payload hash
            const payloadHash = await crypto.subtle.digest('SHA-256', payload);
            const headerHash = chunkBuffer.slice(25, 57);

            if (!this._areBuffersEqual(payloadHash, headerHash)) {
                throw new Error("Chunk integrity check failed: hash mismatch.");
            }

            // Parse header fields
            const currentFileIdBytes = chunkBuffer.slice(0, 16);
            if (!fileId) {
                fileId = this._bytesToUuid(currentFileIdBytes);
                totalChunks = chunkView.getUint32(16, false); // big-endian
                console.log(`[sfln.js] Reassembling File ID: ${fileId}`);
                console.log(`[sfln.js] Expecting ${totalChunks} chunks.`);
            } else if (this._bytesToUuid(currentFileIdBytes) !== fileId) {
                throw new Error("Mixed file IDs in chunk set.");
            }

            const chunkIndex = chunkView.getUint32(20, false); // big-endian
            const isKeyChunk = chunkView.getUint8(24) === 1;

            parsedChunks.set(chunkIndex, { isKeyChunk, payload: new Uint8Array(payload) });
        }

        console.log(`[sfln.js] All ${parsedChunks.size} chunks successfully verified.`);
        if (parsedChunks.size !== totalChunks) {
            throw new Error(`Incomplete data: received ${parsedChunks.size} chunks, but expected ${totalChunks}.`);
        }

        // --- Step 2 & 3: Find Key, Extract Crypto Materials, and Sort ---
        let masterKey, nonce, authTag;
        const encryptedSegments = new Array(totalChunks);

        for (let i = 0; i < totalChunks; i++) {
            const chunkData = parsedChunks.get(i);
            if (!chunkData) {
                throw new Error(`Missing chunk with index ${i}.`);
            }

            if (chunkData.isKeyChunk) {
                console.log(`[sfln.js] Found key in chunk ${i}.`);
                const keyPayload = chunkData.payload;
                masterKey = keyPayload.slice(0, 32);
                nonce = keyPayload.slice(32, 48); // 16 bytes for nonce
                authTag = keyPayload.slice(48, 64); // 16 bytes for auth tag
                encryptedSegments[i] = keyPayload.slice(64);
            } else {
                encryptedSegments[i] = chunkData.payload;
            }
        }

        if (!masterKey || !nonce || !authTag) {
            throw new Error("Failed to find key chunk or crypto materials.");
        }
        console.log("[sfln.js] Extracted master key, nonce, and auth tag.");

        // --- Step 4 & 5: Reassemble and Decrypt ---
        const reassembledPayload = this._concatUint8Arrays(encryptedSegments);
        console.log(`[sfln.js] Reassembled encrypted payload of size ${reassembledPayload.byteLength}.`);

        try {
            const cryptoKey = await crypto.subtle.importKey(
                "raw",
                masterKey,
                { name: "AES-GCM" },
                false, // not extractable
                ["decrypt"]
            );

            // The Web Crypto API combines the ciphertext and auth tag for decryption.
            // We need to append the tag to the ciphertext.
            const dataToDecrypt = this._concatUint8Arrays([reassembledPayload, authTag]);

            const decryptedData = await crypto.subtle.decrypt(
                {
                    name: "AES-GCM",
                    iv: nonce,
                    tagLength: 128, // bits
                },
                cryptoKey,
                dataToDecrypt
            );

            console.log("[sfln.js] Decryption successful!");
            return new Uint8Array(decryptedData);

        } catch (e) {
            console.error("[sfln.js] Decryption failed:", e);
            throw new Error("Decryption failed. Data might be corrupt or key is wrong.");
        }
    },

    /**
     * Helper to convert UUID bytes to a hex string format.
     */
    _bytesToUuid(bytes) {
        const hex = Array.from(bytes, byte => ('0' + (byte & 0xFF).toString(16)).slice(-2));
        return `${hex.slice(0,4).join('')}-${hex.slice(4,6).join('')}-${hex.slice(6,8).join('')}-${hex.slice(8,10).join('')}-${hex.slice(10,16).join('')}`;
    },

    /**
     * Helper to compare two ArrayBuffers.
     */
    _areBuffersEqual(buf1, buf2) {
        if (buf1.byteLength !== buf2.byteLength) return false;
        const view1 = new Uint8Array(buf1);
        const view2 = new Uint8Array(buf2);
        for (let i = 0; i < view1.length; i++) {
            if (view1[i] !== view2[i]) return false;
        }
        return true;
    },

    /**
     * Helper to concatenate multiple Uint8Arrays.
     */
    _concatUint8Arrays(arrays) {
        let totalLength = 0;
        for (const arr of arrays) {
            totalLength += arr.length;
        }
        const result = new Uint8Array(totalLength);
        let offset = 0;
        for (const arr of arrays) {
            result.set(arr, offset);
            offset += arr.length;
        }
        return result;
    }
};
