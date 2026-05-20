/**
 * SFLN Easy Integration Widget v1.0
 * 1-Line implementation for developers.
 */

(function() {
    const DEFAULT_RELAY = "wss://sfln-server.pdg.f5.si:9001";

    class SFLNEasyWidget {
        constructor(containerId, options = {}) {
            this.container = document.getElementById(containerId);
            if (!this.container) {
                console.error(`SFLN: Container #${containerId} not found.`);
                return;
            }
            this.options = Object.assign({
                theme: 'dark',
                primaryColor: '#58a6ff',
                backgroundColor: '#161b22',
                textColor: '#c9d1d9',
                buttonText: 'Secure Send'
            }, options);

            this.client = new SFLNClientJS();
            this.init();
        }

        async init() {
            this.render();
            await this.client.connect(DEFAULT_RELAY);
            this.updateStatus("Ready (Connected)");

            // Auto-pair if hash is present
            if (window.location.hash) {
                const targetId = window.location.hash.substring(1);
                if (targetId.length > 20) {
                    document.getElementById('sfln-target-id').value = targetId;
                    this.updateStatus(`Auto-paired with ${targetId.substring(0,8)}...`);
                }
            }
        }

        updateStatus(text) {
            const el = document.getElementById('sfln-widget-status');
            if (el) el.innerText = text;
        }

        render() {
            const style = `
                .sfln-easy-container {
                    background: ${this.options.backgroundColor};
                    color: ${this.options.textColor};
                    padding: 20px;
                    border-radius: 12px;
                    border: 1px solid #30363d;
                    font-family: 'Segoe UI', sans-serif;
                    max-width: 500px;
                }
                .sfln-header { color: ${this.options.primaryColor}; font-weight: bold; margin-bottom: 15px; display: flex; justify-content: space-between; }
                .sfln-input { width: 100%; background: #0d1117; border: 1px solid #30363d; color: #fff; padding: 10px; border-radius: 6px; margin-bottom: 10px; font-family: monospace; }
                .sfln-button { background: ${this.options.primaryColor}; color: #000; border: none; padding: 10px 20px; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; transition: opacity 0.2s; }
                .sfln-button:hover { opacity: 0.8; }
                .sfln-status { font-size: 0.8rem; color: #8b949e; margin-top: 10px; text-align: center; }
            `;
            const styleTag = document.createElement('style');
            styleTag.textContent = style;
            document.head.appendChild(styleTag);

            this.container.innerHTML = `
                <div class="sfln-easy-container">
                    <div class="sfln-header">
                        <span>SFLN Secure Transfer</span>
                        <small style="font-size: 0.7rem; color: #8b949e;">Node: ${this.client.nodeId.substring(0,8)}...</small>
                    </div>
                    <input type="text" id="sfln-target-id" class="sfln-input" placeholder="Recipient Node ID">
                    <input type="file" id="sfln-file-input" style="display:none">
                    <button class="sfln-button" id="sfln-send-btn">${this.options.buttonText}</button>
                    <div id="sfln-widget-status" class="sfln-status">Initializing...</div>
                </div>
            `;

            document.getElementById('sfln-send-btn').onclick = () => document.getElementById('sfln-file-input').click();
            document.getElementById('sfln-file-input').onchange = (e) => this.handleFile(e);
        }

        async handleFile(e) {
            const file = e.target.files[0];
            const targetId = document.getElementById('sfln-target-id').value.trim();
            if (!file || !targetId) {
                alert("Please select a file and enter a target Node ID.");
                return;
            }

            this.updateStatus(`Encrypting ${file.name}...`);
            const meta = JSON.stringify({ type: 'file_meta', name: file.name, size: file.size });
            await this.client.send(new TextEncoder().encode(meta), targetId);

            const data = new Uint8Array(await file.arrayBuffer());
            await this.client.send(data, targetId, (phase, cur, tot) => {
                this.updateStatus(`[${phase}] ${Math.round(cur/tot*100)}%`);
            });
            this.updateStatus("Transfer Complete!");
        }
    }

    // Expose globally
    window.SFLNEasyWidget = SFLNEasyWidget;
})();
