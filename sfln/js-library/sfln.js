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
        this.peers = [];
        this.ws = null;
        this.onMessage = null;
    }

    async connect(serverUrl) {
        return new Promise((resolve, reject) => {
            console.log(`[SFLN] Connecting as ${this.nodeId} to ${serverUrl}`);
            this.ws = new WebSocket(serverUrl);
            this.ws.binaryType = 'arraybuffer';

            this.ws.onopen = () => {
                this.ws.send(JSON.stringify({
                    type: "register",
                    node_id: this.nodeId
                }));
            };

            this.ws.onmessage = async (event) => {
                if (typeof event.data === 'string') {
                    const msg = JSON.parse(event.data);
                    if (msg.type === "reg_ack") {
                        console.log("[SFLN] Registered successfully");
                        resolve();
                    } else if (msg.type === "peers") {
                        this.peers = msg.list.filter(id => id !== this.nodeId);
                    }
                } else {
                    // Binary relay: [Magic][Type][Payload]
                    const data = new Uint8Array(event.data);
                    if (data[0] === 0x53 && data[1] === 0x02) {
                        const payload = data.slice(2);
                        if (this.onMessage) this.onMessage(payload);
                    }
                }
            };

            this.ws.onerror = (err) => reject(err);
        });
    }

    async refreshPeers() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: "get_peers" }));
        }
    }

    async send(data, targetId) {
        console.log(`[SFLN] Encrypting and sending to ${targetId}`);
        const chunks = await this.crypto.encryptData(data);
        
        // Protocol format for relay: [Magic: 'S'][Type: 0x01][TargetID: 16b][Payload]
        const targetUUIDBytes = this.uuidToBytes(targetId);
        
        for (const chunk of chunks) {
            const packet = new Uint8Array(2 + 16 + chunk.length);
            packet[0] = 0x53;
            packet[1] = 0x01;
            packet.set(targetUUIDBytes, 2);
            packet.set(chunk, 18);
            this.ws.send(packet);
        }
    }

    uuidToBytes(uuid) {
        const hex = uuid.replace(/-/g, '');
        const bytes = new Uint8Array(16);
        for (let i = 0; i < 16; i++) {
            bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
        }
        return bytes;
    }
}

if (typeof module !== 'undefined') {
    module.exports = { SFLNCryptoJS, SFLNClientJS };
}
