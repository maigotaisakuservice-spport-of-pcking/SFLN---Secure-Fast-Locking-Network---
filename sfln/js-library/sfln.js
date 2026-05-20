/**
 * SFLN JavaScript Library v2.2
 * Supports SFLN-P v2.2 Open Standard
 */

class SFLNCryptoJS {
    constructor(masterKey = null) {
        this.KEY_BITS = 40000;
        this.CHUNK_SIZE = 1024;
        this.KEY_EMBED_SIZE = 32;
        if (masterKey) this.masterKey = masterKey;
        else this.masterKey = crypto.getRandomValues(new Uint8Array(this.KEY_BITS / 8));
    }

    async deriveChunkKey(chunkIndex, chunkSeed) {
        const encoder = new TextEncoder();
        const info = encoder.encode(chunkIndex.toString());
        const combined = new Uint8Array(this.masterKey.length + chunkSeed.length + info.length);
        combined.set(this.masterKey);
        combined.set(chunkSeed, this.masterKey.length);
        combined.set(info, this.masterKey.length + chunkSeed.length);
        const hashBuffer = await crypto.subtle.digest('SHA-256', combined);
        return await crypto.subtle.importKey('raw', hashBuffer, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
    }

    async encryptData(data, progressCallback = null) {
        const totalChunks = Math.ceil(data.length / this.CHUNK_SIZE);
        const encryptedChunks = [];
        for (let i = 0; i < data.length; i += this.CHUNK_SIZE) {
            const chunk = data.slice(i, i + this.CHUNK_SIZE);
            const idx = Math.floor(i / this.CHUNK_SIZE);
            const chunkSeed = crypto.getRandomValues(new Uint8Array(this.KEY_EMBED_SIZE));
            const key = await this.deriveChunkKey(idx, chunkSeed);
            const nonce = crypto.getRandomValues(new Uint8Array(12));
            const encryptedBuffer = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce }, key, chunk);
            encryptedChunks.push({ index: idx, data: new Uint8Array(12 + this.KEY_EMBED_SIZE + encryptedBuffer.byteLength), nonce, chunkSeed, encryptedBuffer });
            const p = encryptedChunks[encryptedChunks.length - 1];
            p.data.set(nonce);
            p.data.set(chunkSeed, 12);
            p.data.set(new Uint8Array(encryptedBuffer), 12 + this.KEY_EMBED_SIZE);

            if (progressCallback && idx % 100 === 0) {
                progressCallback(idx, totalChunks);
            }
        }
        if (progressCallback) progressCallback(totalChunks, totalChunks);
        return encryptedChunks;
    }

    async decryptChunk(chunkData, index) {
        const nonce = chunkData.slice(0, 12);
        const chunkSeed = chunkData.slice(12, 12 + this.KEY_EMBED_SIZE);
        const encryptedPayload = chunkData.slice(12 + this.KEY_EMBED_SIZE);
        const key = await this.deriveChunkKey(index, chunkSeed);
        const decryptedBuffer = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: nonce }, key, encryptedPayload);
        return new Uint8Array(decryptedBuffer);
    }
}

class SFLNClientJS {
    constructor(masterKey = null, nodeId = null) {
        this.crypto = new SFLNCryptoJS(masterKey);
        this.nodeId = nodeId || this.generateUUID();
        this.ws = null;
        this.onMessage = null;
        this.onProgress = null;
        this.activeTransfers = new Map();
        this.isVerified = false;
        this.pendingMetadata = new Map();
        this.serverUrl = null;
        this.reconnectAttempts = 0;
        this.maxReconnectDelay = 30000;
    }

    async verifyAppPresence() {
        try {
            // Using a low timeout to prevent UI hanging on slow-refusing local ports
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 1000);
            const res = await fetch('http://localhost:49000/status', { signal: controller.signal });
            clearTimeout(timeout);
            this.isVerified = res.ok;
        } catch (e) {
            this.isVerified = false;
            // Silent failure for app detection - common in browser environments
        }
        return this.isVerified;
    }

    async connect(serverUrl) {
        this.serverUrl = serverUrl;
        let wsUrl = serverUrl;
        if (wsUrl.startsWith("https://")) wsUrl = wsUrl.replace("https://", "wss://");

        return new Promise((resolve, reject) => {
            if (this.ws) {
                this.ws.onopen = null;
                this.ws.onmessage = null;
                this.ws.onclose = null;
                this.ws.onerror = null;
                this.ws.close();
            }

            this.ws = new WebSocket(wsUrl);
            this.ws.binaryType = 'arraybuffer';

            const timeout = setTimeout(() => {
                if (this.ws.readyState !== WebSocket.OPEN) {
                    this.ws.close();
                    reject(new Error("Connection timeout"));
                }
            }, 10000);

            this.ws.onopen = () => {
                clearTimeout(timeout);
                this.reconnectAttempts = 0;
                this.ws.send(JSON.stringify({ type: "register", node_id: this.nodeId }));
            };

            this.ws.onclose = () => {
                clearTimeout(timeout);
                this.handleReconnect();
            };

            this.ws.onerror = (err) => {
                clearTimeout(timeout);
                console.error("SFLN WebSocket Error:", err);
            };

            this.ws.onmessage = async (event) => {
                if (typeof event.data === 'string') {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'reg_ack') resolve();
                } else {
                    const data = new Uint8Array(event.data);
                    // Standard SFLN-P v2 packet (Relayed)
                    if (data[0] === 0x53 && (data[1] >> 4) === 0x2) {
                        const sourceId = this.bytesToUuid(data.slice(3, 19));
                        const dv = new DataView(data.buffer, data.byteOffset);
                        const seq = dv.getUint32(35);
                        const total = dv.getUint32(39);
                        this.handleReceivedChunk(sourceId, seq, total, data.slice(43));
                    }
                }
            };
        });
    }

    handleReconnect() {
        const delay = Math.min(Math.pow(2, this.reconnectAttempts) * 1000, this.maxReconnectDelay);
        this.reconnectAttempts++;
        console.log(`SFLN: Attempting reconnect in ${delay}ms... (Attempt ${this.reconnectAttempts})`);
        setTimeout(() => this.connect(this.serverUrl), delay);
    }

    async handleReceivedChunk(senderId, index, total, encryptedData) {
        if (!this.activeTransfers.has(senderId)) this.activeTransfers.set(senderId, { chunks: new Map(), total: total });
        const transfer = this.activeTransfers.get(senderId);
        const decrypted = await this.crypto.decryptChunk(encryptedData, index);
        transfer.chunks.set(index, decrypted);

        if (this.onProgress) this.onProgress("RECEIVING", transfer.chunks.size, total);

        if (transfer.chunks.size === total) {
            const sorted = Array.from(transfer.chunks.entries()).sort((a,b) => a[0]-b[0]).map(x => x[1]);
            const fullData = new Uint8Array(sorted.reduce((a,b) => a + b.length, 0));
            let offset = 0;
            for (const p of sorted) { fullData.set(p, offset); offset += p.length; }

            // Check for metadata
            try {
                const text = new TextDecoder().decode(fullData);
                const msg = JSON.parse(text);
                if (msg.type === 'file_meta') {
                    this.pendingMetadata.set(senderId, msg);
                    this.activeTransfers.delete(senderId);
                    return;
                }
            } catch (e) {}

            const meta = this.pendingMetadata.get(senderId);
            if (this.onMessage) this.onMessage(fullData, senderId, meta ? meta.name : "received_file");
            this.activeTransfers.delete(senderId);
            this.pendingMetadata.delete(senderId);
        }
    }

    async send(data, targetId, progressCallback = null) {
        const encryptedChunks = await this.crypto.encryptData(data, (cur, tot) => {
            if (progressCallback) progressCallback("ENCRYPTING", cur, tot);
        });

        const targetUUID = this.uuidToBytes(targetId);
        const myUUID = this.uuidToBytes(this.nodeId);
        const total = encryptedChunks.length;

        for (let i = 0; i < encryptedChunks.length; i++) {
            const chunk = encryptedChunks[i];
            const packet = new Uint8Array(43 + chunk.data.length);
            packet[0] = 0x53;
            packet[1] = (0x2 << 4) | 0x0; // SFLN-P v2 Data
            packet[2] = 0x0; // Hop Count
            packet.set(myUUID, 3);
            packet.set(targetUUID, 19);
            const dv = new DataView(packet.buffer, packet.byteOffset);
            dv.setUint32(35, i);
            dv.setUint32(39, total);
            packet.set(chunk.data, 43);
            this.ws.send(packet);

            if (progressCallback && i % 100 === 0) {
                progressCallback("TRANSFERRING", i, total);
            }
        }
    }

    generateUUID() { return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => (Math.random()*16|0).toString(16)); }
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

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SFLNCryptoJS, SFLNClientJS };
}
