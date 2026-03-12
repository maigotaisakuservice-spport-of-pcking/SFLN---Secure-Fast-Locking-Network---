# SFLN (Secure-Fast-Locking-Network) 開発・利用ガイド

SFLN は、12,000桁暗号と 1GB/s ターゲットを両立させた次世代 P2P メッシュネットワークです。

---

## 📱 クライアント・アプリケーション

一般利用者向けの多機能クライアントです。

### 1. デスクトップ GUI 版 (Win / Linux / Mac)
QRコードによる簡単なデバイス連携が可能です。
- **Dashboard**: ワンクリックで接続。
- **Pairing**: 自分の Node ID を QR コードで表示。相手の ID を入力して「ペアリング」することで、セキュアな直接ファイル送信が可能になります。
- **Security**: アプリやドメインごとの除外設定。

### 2. 高性能 CUI 版 (Win Server / Linux Server)
サーバー環境での 24/7 稼働に特化した軽量・高効率クライアントです。

---

## 🛠️ ライブラリの役割とユースケース

SFLN SDK は、既存のシステムに「最強の暗号化」と「自律型ネットワーク」を組み込むために設計されています。

### 💡 なにに使えるの？ (ユースケース)
1. **機密情報の超高速共有**:
   - 12,000桁暗号により、機密性の高い設計図や金融データ（GB級）を、既存のインターネットを経由せずに（またはリレーして）安全に転送。
2. **Web ベースのセキュアチャット/コラボツール**:
   - `JS SDK` を Web ページに埋め込むだけで、サーバーに一切の情報を残さない「完全秘匿型の P2P 通信」を実現。
3. **IoT デバイスのセキュア制御**:
   - `Python SDK` を使い、外出先から自宅・工場の機器を暗号化メッシュ経由で安全に操作（VPN 設定不要）。
4. **検閲耐性のあるインフラ**:
   - 中央サーバーに頼らない自己増殖型ネットワークにより、通信の遮断が困難なネットワークを構築。

---

## 🚀 開発者向けリファレンス

### JavaScript SDK
```javascript
const client = new SFLNClientJS();
await client.connect('wss://sfln-server.pdg.f5.si');
client.onMessage = (data, senderId) => { /* 復号済みデータの受信処理 */ };
await client.send(uint8ArrayData, "TARGET_ID");
```

### Python SDK
```python
from sfln.python_library.sdk import SFLNSDK
sdk = SFLNSDK()
await sdk.connect([("sfln-server.pdg.f5.si", 9000)])
await sdk.send(b"Secret", "TARGET_ID")
```

---

## 📝 運用と自動化
- **サーバー運用**: 詳細な手順は **[SERVER.md](SERVER.md)** を参照。
- **自動ビルド**: GitHub Actions により、常に最新のバイナリが公式サイト (`index.html`) から提供されます。
