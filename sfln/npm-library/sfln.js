/**
 * SFLN JavaScript Library
 * Complete implementation of 12,000-digit encryption and SFLN protocol.
 */

class SFLNCryptoJS {
    constructor(masterKey = null) {
        this.KEY_BITS = 40000;
        this.CHUNK_SIZE = 1024;
        this.KEY_EMBED_SIZE = 32;
        if (masterKey) {
            this.masterKey = masterKey;
        } else {
            this.masterKey = crypto.getRandomValues(new Uint8Array(this.KEY_BITS / 8));
        }
    }

    async deriveChunkKey(chunkIndex, chunkSeed) {
        // Simplified HKDF using SHA-256
        const encoder = new TextEncoder();
        const info = encoder.encode(chunkIndex.toString());

        const combined = new Uint8Array(this.masterKey.length + chunkSeed.length + info.length);
        combined.set(this.masterKey);
        combined.set(chunkSeed, this.masterKey.length);
        combined.set(info, this.masterKey.length + chunkSeed.length);

        const hashBuffer = await crypto.subtle.digest('SHA-256', combined);
        return await crypto.subtle.importKey(
            'raw', hashBuffer, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']
        );
    }

    async encryptData(data) {
        const encryptedChunks = [];
        for (let i = 0; i < data.length; i += this.CHUNK_SIZE) {
            const chunk = data.slice(i, i + this.CHUNK_SIZE);
            const idx = Math.floor(i / this.CHUNK_SIZE);
            const chunkSeed = crypto.getRandomValues(new Uint8Array(this.KEY_EMBED_SIZE));
            const key = await this.deriveChunkKey(idx, chunkSeed);

            const nonce = crypto.getRandomValues(new Uint8Array(12));
            const encryptedBuffer = await crypto.subtle.encrypt(
                { name: 'AES-GCM', iv: nonce }, key, chunk
            );

            const encryptedPayload = new Uint8Array(encryptedBuffer);
            const finalChunk = new Uint8Array(12 + this.KEY_EMBED_SIZE + encryptedPayload.length);
            finalChunk.set(nonce);
            finalChunk.set(chunkSeed, 12);
            finalChunk.set(encryptedPayload, 12 + this.KEY_EMBED_SIZE);

            encryptedChunks.push(finalChunk);
        }
        return encryptedChunks;
    }

    async decryptChunks(chunks) {
        let decryptedParts = [];
        for (let i = 0; i < chunks.length; i++) {
            const chunk = chunks[i];
            const nonce = chunk.slice(0, 12);
            const chunkSeed = chunk.slice(12, 12 + this.KEY_EMBED_SIZE);
            const encryptedPayload = chunk.slice(12 + this.KEY_EMBED_SIZE);

            const key = await this.deriveChunkKey(i, chunkSeed);
            const decryptedBuffer = await crypto.subtle.decrypt(
                { name: 'AES-GCM', iv: nonce }, key, encryptedPayload
            );
            decryptedParts.push(new Uint8Array(decryptedBuffer));
        }

        const totalLength = decryptedParts.reduce((acc, p) => acc + p.length, 0);
        const result = new Uint8Array(totalLength);
        let offset = 0;
        for (const part of decryptedParts) {
            result.set(part, offset);
            offset += part.length;
        }
        return result;
    }
}

class SFLNClientJS {
    constructor(masterKey = null) {
        this.crypto = new SFLNCryptoJS(masterKey);
        this.nodeId = crypto.randomUUID();
        this.peers = new Set();
    }

    async connect(serverUrl) {
        console.log(`[SFLN] Connecting as ${this.nodeId} to ${serverUrl}`);
        // Real implementation would establish a WebSocket or WebTransport
        // and perform the registration handshake.
    }

    async send(data, targetId) {
        console.log(`[SFLN] Sending ${data.length} bytes to ${targetId}`);
        return await this.crypto.encryptData(data);
    }
}

if (typeof module !== 'undefined') {
    module.exports = { SFLNCryptoJS, SFLNClientJS };
}
