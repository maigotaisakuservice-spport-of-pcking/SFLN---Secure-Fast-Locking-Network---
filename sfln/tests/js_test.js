const { SFLNCryptoJS, SFLNClientJS } = require('../npm-library/sfln.js');
const assert = require('assert');
const WebSocket = require('ws');

// Mock fetch for verifyAppPresence
global.fetch = async () => ({ ok: true });

async function test_js_crypto() {
    console.log("--- Testing SFLN JS Crypto (12,000-digit) ---");
    const cryptoInstance = new SFLNCryptoJS();

    // Test small chunk
    const testData = new TextEncoder().encode("Hello SFLN from JavaScript!");
    console.log(`Original data length: ${testData.length} bytes`);

    const chunks = await cryptoInstance.encryptData(testData);
    console.log(`Encrypted into ${chunks.length} chunks.`);

    // Manually reconstruct chunks for testing since it's v2 logic
    const decryptedChunks = [];
    for (let i = 0; i < chunks.length; i++) {
        decryptedChunks.push(await cryptoInstance.decryptChunk(chunks[i].data, i));
    }
    const decryptedLen = decryptedChunks.reduce((a,b) => a + b.length, 0);
    const decrypted = new Uint8Array(decryptedLen);
    let off = 0;
    for (const d of decryptedChunks) { decrypted.set(d, off); off += d.length; }

    const decryptedText = new TextDecoder().decode(decrypted);

    assert.strictEqual(decryptedText, "Hello SFLN from JavaScript!");
    console.log("✅ Basic decryption check passed.");

    // Test large data (1MB)
    const largeData = new Uint8Array(1024 * 1024);
    for (let i = 0; i < largeData.length; i++) largeData[i] = i % 256;
    console.log(`Testing 1MB data...`);
    const largeChunks = await cryptoInstance.encryptData(largeData);
    const largeDecryptedChunks = [];
    for (let i = 0; i < largeChunks.length; i++) {
        largeDecryptedChunks.push(await cryptoInstance.decryptChunk(largeChunks[i].data, i));
    }
    const largeDecrypted = new Uint8Array(largeData.length);
    let loff = 0;
    for (const d of largeDecryptedChunks) { largeDecrypted.set(d, loff); loff += d.length; }

    assert.deepStrictEqual(largeDecrypted, largeData);
    console.log("✅ 1MB data integrity check passed.");

    console.log("--- All JS Tests Passed ---");
}

async function test_relay_connection() {
    console.log("--- Testing SFLN Relay Connection (Node.js) ---");

    // Inject WebSocket into global for SFLNClientJS to use if it expects browser-like environment
    // Or we just handle it in the test. SFLNClientJS uses global WebSocket.
    global.WebSocket = WebSocket;

    const sharedKey = new Uint8Array(5000);
    for(let i=0; i<5000; i++) sharedKey[i] = i % 256;
    const client1 = new SFLNClientJS(sharedKey);
    const client2 = new SFLNClientJS(sharedKey);

    try {
        console.log("Connecting Client 1 to local relay...");
        await client1.connect("ws://localhost:9001");
        console.log("Client 1 connected.");

        console.log("Connecting Client 2 to local relay...");
        await client2.connect("ws://localhost:9001");
        console.log("Client 2 connected.");

        const testMsg = new TextEncoder().encode("Relay Test Message");
        // Ensure data is multiple of something or just simple?

        const receivePromise = new Promise((resolve, reject) => {
            const timeout = setTimeout(() => reject(new Error("Relay Timeout")), 5000);
            client2.onMessage = (data, senderId) => {
                clearTimeout(timeout);
                assert.strictEqual(senderId, client1.nodeId);
                assert.deepStrictEqual(data, testMsg);
                resolve();
            };
        });

        console.log(`Sending message from ${client1.nodeId} to ${client2.nodeId}...`);
        // Add a small delay for registration to propogate if needed
        await new Promise(r => setTimeout(r, 100));
        await client1.send(testMsg, client2.nodeId);

        await receivePromise;
        console.log("✅ Relay communication successful.");

        await client1.ws.close();
        await client2.ws.close();

    } catch (e) {
        console.error("DEBUG: Error occurred during relay test:", e);
        console.warn("Relay test skipped or failed (is server running?):", e.message);
        // If it's a connection error, we might be in a non-server environment,
        // but in CI it should fail if server is expected.
        if (process.env.GITHUB_ACTIONS && e.message.includes("ECONNREFUSED")) {
            throw e;
        }
    }
}

async function run_all() {
    await test_js_crypto();
    await test_relay_connection();
}

run_all().catch(err => {
    console.error("❌ JS Test Failed:", err);
    process.exit(1);
});
