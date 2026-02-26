# SFLN (Secure-Fast-Locking-Network) セットアップガイド

SFLNサービス、サーバー、およびクライアントのセットアップ方法について説明します。

## 1. サーバーのセットアップ (Ubuntu/Linux推奨)

サーバーは、クライアント間の通信を中継し、メッシュネットワークを調整する役割を果たします。

### 手順:
1.  **依存関係のインストール**:
    ```bash
    cd sfln/server
    pip install -r requirements.txt
    ```

2.  **サーバーの起動**:
    デフォルトでポート `9000` (UDP) を使用します。ファイアウォールでこのポートを開放してください。
    ```bash
    python3 main.py
    ```
    ※ 本番環境では、`systemd` 等を使用してバックグラウンドで実行することを推奨します。

---

## 2. クライアント(GUI)のセットアップ (Windows/Linux)

### 手順:
1.  **依存関係のインストール**:
    ```bash
    cd sfln/client
    pip install -r requirements.txt
    ```

2.  **クライアントの起動**:
    ```bash
    python3 gui.py
    ```

### 使い方:
- **Dashboard**: 「ENABLE SFLN」をクリックして接続を開始します。
- **Excluded Apps**: 除外したいアプリを選択し、右下の「Refresh」で反映させます。
- **Excluded Sites**: 除外したいドメイン（google.comなど）を入力して「Add」します。
- **Excluded Users**: SFLNを適用したくないシステムユーザーを選択します。

---

## 3. ライブラリの使用方法

### Python SDK:
```python
from sfln.python_library.sdk import SFLNSDK
import asyncio

async def main():
    sdk = SFLNSDK()
    # サーバーのアドレスを指定して接続
    await sdk.connect([("your-server-ip", 9000)])
    await sdk.send(b"Hello SFLN", ("target-node-id", 0))

asyncio.run(main())
```

### JavaScript / npm:
```javascript
const { SFLNClientJS } = require('./sfln.js');
const client = new SFLNClientJS();
await client.connect('ws://your-server-ip:9000');
```

---

## 4. 検証テストの実行
すべての機能が正しく動作するか確認するには、以下のコマンドを実行してください。

**基本機能テスト (暗号化・認証など):**
```bash
python3 sfln/tests/full_test.py
```

**統合通信テスト (サーバーを介したリレー通信):**
```bash
python3 sfln/tests/integration_test.py
```

**パフォーマンス計測 (10MB 〜 1TB):**
```bash
# 1GBのテスト
python3 sfln/tests/performance_test.py --size 1.0

# 1TBのテスト (ストリーミング方式でディスク消費なし)
python3 sfln/tests/performance_test.py --size 1024.0
```

**詳細検証テスト:**
```bash
# カオス/AIルーティングテスト
python3 sfln/tests/chaos_test.py

# サーバー高負荷テスト
python3 sfln/tests/load_test.py

# JavaScriptライブラリテスト
node sfln/tests/js_test.js
```

## 5. デプロイと運用に関する重要事項

### GitHub Actionsでの運用について
**注意：** GitHub Actions上で本番用のSFLNサーバーを常時稼働させたり、大量の通信（リレー）を行ったりすることは、**GitHubの利用規約(ToS)違反**となる可能性が非常に高いです。

- **Actionsの用途**: 継続的インテリジェンス(CI)としての自動テストに使用してください（`.github/workflows/sfln-ci.yml` を同梱済み）。
- **推奨されるサーバーホスティング**: 高速な通信を実現するためには、UDPトラフィックが許可されており、帯域制限の緩いVPS（AWS, GCP, DigitalOcean, Hetzner等）での運用を強く推奨します。

### サーバーのデプロイ手順例 (Linux VPS)
1. サーバー上でリポジトリをクローン。
2. `sfln/server` 内で依存関係をインストール。
3. ポート `9000/udp` を開放。
4. `systemd` を使用してサービス化し、自動起動を設定。
