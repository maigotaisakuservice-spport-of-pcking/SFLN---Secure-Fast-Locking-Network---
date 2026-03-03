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
            // Check for crypto availability
            if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
                this.masterKey = crypto.getRandomValues(new Uint8Array(this.KEY_BITS / 8));
            } else {
                // Fallback for Node.js or environments without global crypto
                this.masterKey = new Uint8Array(this.KEY_BITS / 8).fill(0).map(() => Math.floor(Math.random() * 256));
            }
        }
    }

    async deriveChunkKey(chunkIndex, chunkSeed) {
        const encoder = new TextEncoder();
        const info = encoder.encode(chunkIndex.toString());

        const combined = new Uint8Array(this.masterKey.length + chunkSeed.length + info.length);
        combined.set(this.masterKey);
        combined.set(chunkSeed, this.masterKey.length);
        combined.set(info, this.masterKey.length + chunkSeed.length);

        const subtle = (typeof crypto !== 'undefined' && crypto.subtle) ? crypto.subtle : null;
        if (!subtle) throw new Error("WebCrypto not supported in this environment");

        const hashBuffer = await subtle.digest('SHA-256', combined);
        return await subtle.importKey(
            'raw', hashBuffer, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']
        );
    }

    async encryptData(data) {
        const encryptedChunks = [];
        const subtle = (typeof crypto !== 'undefined' && crypto.subtle) ? crypto.subtle : null;
        if (!subtle) throw new Error("WebCrypto not supported");

        for (let i = 0; i < data.length; i += this.CHUNK_SIZE) {
            const chunk = data.slice(i, i + this.CHUNK_SIZE);
            const idx = Math.floor(i / this.CHUNK_SIZE);
            const chunkSeed = crypto.getRandomValues(new Uint8Array(this.KEY_EMBED_SIZE));
            const key = await this.deriveChunkKey(idx, chunkSeed);

            const nonce = crypto.getRandomValues(new Uint8Array(12));
            const encryptedBuffer = await subtle.encrypt(
                { name: 'AES-GCM', iv: nonce }, key, chunk
            );

            const encryptedPayload = new Uint8Array(encryptedBuffer);
            const finalChunk = new Uint8Array(12 + this.KEY_EMBED_SIZE + encryptedPayload.length);
            finalChunk.set(nonce);
            finalChunk.set(chunkSeed, 12);
            finalChunk.set(encryptedPayload, 12 + this.KEY_EMBED_SIZE);

            encryptedChunks.push({ index: idx, data: finalChunk });
        }
        return encryptedChunks;
    }

    async decryptChunk(chunkData, index) {
        const subtle = (typeof crypto !== 'undefined' && crypto.subtle) ? crypto.subtle : null;
        if (!subtle) throw new Error("WebCrypto not supported");

        const nonce = chunkData.slice(0, 12);
        const chunkSeed = chunkData.slice(12, 12 + this.KEY_EMBED_SIZE);
        const encryptedPayload = chunkData.slice(12 + this.KEY_EMBED_SIZE);

        const key = await this.deriveChunkKey(index, chunkSeed);
        const decryptedBuffer = await subtle.decrypt(
            { name: 'AES-GCM', iv: nonce }, key, encryptedPayload
        );
        return new Uint8Array(decryptedBuffer);
    }

    async decryptChunks(chunks) {
        let decryptedParts = [];
        for (let i = 0; i < chunks.length; i++) {
            const chunkObj = chunks[i];
            const data = (chunkObj instanceof Uint8Array) ? chunkObj : chunkObj.data;
            const idx = (chunkObj instanceof Uint8Array) ? i : chunkObj.index;
            const decrypted = await this.decryptChunk(data, idx);
            decryptedParts.push(decrypted);
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
    constructor(masterKey = null, nodeId = null) {
        this.crypto = new SFLNCryptoJS(masterKey);
        this.nodeId = nodeId || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : this.generateUUID());
        this.ws = null;
        this.onMessage = null;
        this.onProgress = null;
        this.onReady = null;
        this.activeTransfers = new Map();
    }

    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    async connect(serverUrl) {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(serverUrl);
                this.ws.binaryType = 'arraybuffer';

                this.ws.onopen = () => {
                    this.ws.send(JSON.stringify({ type: "register", node_id: this.nodeId }));
                };

                this.ws.onmessage = async (event) => {
                    if (typeof event.data === 'string') {
                        const msg = JSON.parse(event.data);
                        if (msg.type === 'reg_ack') {
                            if (this.onReady) this.onReady();
                            resolve();
                        }
                    } else {
                        const data = new Uint8Array(event.data);
                        if (data[0] === 0x53 && data[1] === 0x02) {
                            const sourceId = this.bytesToUuid(data.slice(2, 18));
                            const totalChunks = new DataView(data.buffer, 18, 4).getUint32(0);
                            const chunkIdx = new DataView(data.buffer, 22, 4).getUint32(0);
                            const encryptedData = data.slice(26);
                            this.handleReceivedChunk(sourceId, chunkIdx, totalChunks, encryptedData);
                        }
                    }
                };

                this.ws.onerror = (err) => {
                    console.error("[SFLN] WebSocket error", err);
                    reject(new Error("WebSocket connection failed"));
                };

                this.ws.onclose = () => {
                    console.log("[SFLN] WebSocket closed");
                };

                // Timeout
                setTimeout(() => reject(new Error("Connection timeout")), 5000);

            } catch (err) {
                reject(err);
            }
        });
    }

    async handleReceivedChunk(senderId, index, total, encryptedData) {
        if (!this.activeTransfers.has(senderId)) {
            this.activeTransfers.set(senderId, { chunks: new Map(), total: total });
        }
        const transfer = this.activeTransfers.get(senderId);
        const decrypted = await this.crypto.decryptChunk(encryptedData, index);
        transfer.chunks.set(index, decrypted);
        if (this.onProgress) this.onProgress(transfer.chunks.size, total);
        if (transfer.chunks.size === total) {
            const sortedParts = Array.from(transfer.chunks.entries()).sort((a,b) => a[0]-b[0]).map(x => x[1]);
            const totalLen = sortedParts.reduce((a,b) => a + b.length, 0);
            const fullData = new Uint8Array(totalLen);
            let offset = 0;
            for (const p of sortedParts) { fullData.set(p, offset); offset += p.length; }
            if (this.onMessage) this.onMessage(fullData, senderId);
            this.activeTransfers.delete(senderId);
        }
    }

    async send(data, targetId) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) throw new Error("WebSocket not open");
        const encryptedChunks = await this.crypto.encryptData(data);
        const targetUUID = this.uuidToBytes(targetId);
        const total = encryptedChunks.length;
        for (const chunk of encryptedChunks) {
            const packet = new Uint8Array(2 + 16 + 4 + 4 + chunk.data.length);
            packet[0] = 0x53; packet[1] = 0x01;
            packet.set(targetUUID, 2);
            new DataView(packet.buffer).setUint32(18, total);
            new DataView(packet.buffer).setUint32(22, chunk.index);
            packet.set(chunk.data, 26);
            this.ws.send(packet);
        }
    }

    uuidToBytes(uuidStr) {
        const hex = uuidStr.replace(/-/g, '');
        const bytes = new Uint8Array(16);
        for (let i = 0; i < 16; i++) bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
        return bytes;
    }

    bytesToUuid(bytes) {
        const hex = Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
        return `${hex.substr(0,8)}-${hex.substr(8,4)}-${hex.substr(12,4)}-${hex.substr(16,4)}-${hex.substr(20)}`;
    }
}

if (typeof module !== 'undefined') {
    module.exports = { SFLNCryptoJS, SFLNClientJS };
}
