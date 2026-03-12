# SFLN (Secure-Fast-Locking-Network) 開発・利用ガイド

SFLN は、12,000桁暗号と 1GB/s ターゲットを両立させた次世代 P2P メッシュネットワークです。

---

## 🛠️ 開発者向けリファレンス (サーバーアクセス方法)

### 1. JavaScript SDK (ブラウザ)
Web サイトから SFLN ネットワークに接続し、暗号化データを送受信します。

**接続コード例:**
```javascript
// ライブラリのインポート (js-library/sfln.js)
const client = new SFLNClientJS();

// サーバーに接続 (WebSocket経由)
await client.connect('wss://sfln-server.pdg.f5.si');

// データ受信時のハンドラ
client.onMessage = (data, senderId) => {
    console.log(`Node ${senderId} から受信:`, data);
};

// 相手の ID を指定してデータを送信 (自動 12,000桁暗号化)
await client.send(new Uint8Array([1,2,3]), "TARGET_NODE_ID");
```

### 2. Python SDK (ネイティブ)
アプリケーションのバックエンドとして SFLN を利用します。

**接続コード例:**
```python
from sfln.python_library.sdk import SFLNSDK
import asyncio

async def main():
    sdk = SFLNSDK()

    # サーバー(Backbone)のアドレスを指定して接続
    # UDP ポート 9000 を使用します
    await sdk.connect([("sfln-server.pdg.f5.si", 9000)])

    # 相手ノード ID を指定してセキュア送信
    await sdk.send(b"Top Secret Data", "TARGET_NODE_ID")

asyncio.run(main())
```

---

## 📱 クライアント・アプリケーション (バイナリ)

以下の 6 種類の最新版は公式サイト (`index.html`) からいつでもダウンロード可能です。

1. **Desktop GUI**: Win / Linux / Mac (PySide6 インターフェース)
2. **Server CUI**: Win Server / Linux Server (CUI 最適化、最高効率)
3. **Mobile**: Android (Beta APK)

---

## 🚀 システム自動化 (GitHub Actions)

### 自動ビルド & 公開 (`sfln-build.yml`)
コード更新時に全 6 種のバイナリを自動ビルドし、`client-apps/` への公開と `index.html` のリンク更新を完結させます。

### 自動テスト (`sfln-ci.yml`)
- **1TB 転送計測**: 大容量ストリーミングのスループット検証。
- **カオステスト**: AI ルーティングの動的な経路選択の正確性。
- **負荷テスト**: 100クライアント以上の同時処理。

---

## 📝 サーバーの運用について
リレーサーバーの構築・詳細な運用手順については **[SERVER.md](SERVER.md)** を参照してください。
