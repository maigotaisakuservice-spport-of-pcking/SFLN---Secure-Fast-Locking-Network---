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
```bash
python3 sfln/tests/full_test.py
```
