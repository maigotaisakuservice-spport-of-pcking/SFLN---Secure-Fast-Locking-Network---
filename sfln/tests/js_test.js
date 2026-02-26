const { SFLNCryptoJS } = require('../js-library/sfln.js');
const assert = require('assert');

async function test_js_crypto() {
    console.log("--- Testing SFLN JS Crypto (12,000-digit) ---");
    const cryptoInstance = new SFLNCryptoJS();

    // Test small chunk
    const testData = new TextEncoder().encode("Hello SFLN from JavaScript!");
    console.log(`Original data length: ${testData.length} bytes`);

    const chunks = await cryptoInstance.encryptData(testData);
    console.log(`Encrypted into ${chunks.length} chunks.`);

    const decrypted = await cryptoInstance.decryptChunks(chunks);
    const decryptedText = new TextDecoder().decode(decrypted);

    assert.strictEqual(decryptedText, "Hello SFLN from JavaScript!");
    console.log("✅ Basic decryption check passed.");

    // Test large data (1MB)
    const largeData = new Uint8Array(1024 * 1024);
    for (let i = 0; i < largeData.length; i++) largeData[i] = i % 256;
    console.log(`Testing 1MB data...`);
    const largeChunks = await cryptoInstance.encryptData(largeData);
    const largeDecrypted = await cryptoInstance.decryptChunks(largeChunks);

    assert.deepStrictEqual(largeDecrypted, largeData);
    console.log("✅ 1MB data integrity check passed.");

    console.log("--- All JS Tests Passed ---");
}

test_js_crypto().catch(err => {
    console.error("❌ JS Test Failed:", err);
    process.exit(1);
});
