/**
 * SFLN Node.js Library
 */
const { SFLNCryptoJS, SFLNClientJS } = require('../js-library/sfln.js');
const WebSocket = require('ws');

// In Node.js environment, we need to inject WebSocket and Crypto
if (typeof window === 'undefined') {
    global.WebSocket = WebSocket;
    // For Node.js < 19, we might need a polyfill, but 20+ has it
    if (!global.crypto) {
        global.crypto = require('crypto').webcrypto;
    }
}

module.exports = { SFLNCryptoJS, SFLNClientJS };
