# SFLN (Secure-Fast-Locking-Network) セットアップガイド

SFLNサービス、サーバー、およびクライアントのセットアップ方法について説明します。

## 🚀 クイックスタート (デモ)

GitHub Actions を使用して、自分専用の一時的なリレーサーバーを即座に起動し、遠隔地との暗号化通信をテストできます。

1.  **GitHub Secrets の設定**:
    リポジトリの `Settings > Secrets and variables > Actions` にて、以下のシークレットを登録してください。
    - **Name**: `F5_SI_API_TOKEN`
    - **Secret**: `2d4a704921a716d36bd7dfa3a3d8d74e` (ご提示いただいたキー)
2.  **サーバーの起動**:
    GitHub リポジトリの `Actions` タブから `SFLN Server & Dynamic DNS Update` を選択し、`Run workflow` をクリックします。
    - これにより、`sfln-server.pdg.f5.si` が自動的に起動したサーバーに紐付けられます。
3.  **デモページにアクセス**:
    ブラウザで `demo.html` を開きます。
4.  **ペアリングと送信**:
    - Aさんが「リモートテスト」を選択し、表示されたQRコードまたはIDをBさんに伝えます。
    - BさんがそのIDを入力して「ペアリング」し、ファイルを送信します。
    - 12,000桁の暗号化を施されたデータが、世界中のどこからでも安全にリレーされます。

---

## 🛠️ 開発者向け導入ガイド

### Webサイト・アプリへの導入 (JavaScript)

わずか数行で、既存のWebサイトに最強の暗号化通信を追加できます。

```html
<!-- ライブラリの読み込み -->
<script src="sfln/js-library/sfln.js"></script>

<script>
  const client = new SFLNClientJS();

  // サーバーに接続 (デフォルトのリレーサーバーを使用)
  await client.connect('wss://sfln-server.pdg.f5.si');

  // データ受信時の処理
  client.onMessage = (data, senderId) => {
    console.log(`${senderId} から安全に受信・復号されたデータ:`, data);
  };

  // 相手のノードIDを指定してデータを送信 (自動で12,000桁暗号化)
  await client.send(new Uint8Array([1, 2, 3]), "TARGET_NODE_ID");
</script>
```

### サーバーのセットアップ (Python/Docker)

自前のリレーサーバーを構築する場合の手順です。

1.  **依存関係のインストール**:
    ```bash
    pip install -r sfln/server/requirements.txt
    ```

2.  **サーバーの起動**:
    UDP (9000) と WebSocket (9001) の両方で待ち受けを開始します。
    ```bash
    python3 sfln/server/main.py
    ```

---

## 🧪 テストと検証

### 継続的インテグレーション (CI)
`.github/workflows/sfln-ci.yml` が同梱されており、`push` ごとに以下のテストが自動実行されます：
- Python コア機能テスト
- WebSocket 統合リレーテスト
- JavaScript / NPM ライブラリ互換性テスト

### 手動テスト
```bash
# 全機能統合テスト
python3 sfln/tests/full_test.py

# JSライブラリテスト (Node.js)
node sfln/tests/js_test.js
```

---

## 📝 運用に関する重要事項

### GitHub Actionsでの運用
同梱の `sfln-server.yml` は**テストおよびデモ目的**のものです。
- Cloudflare Tunnel を使用して外部公開し、`f5.si` DDNS を自動更新します。
- 長時間の運用や商用利用には、VPS（AWS, GCP等）へのデプロイを推奨します。

### セキュリティ
SFLNは、12,000桁のマスターキーから派生した一時的な鍵を使用し、AES-GCM 1KB チャンク単位で暗号化を行います。これにより、量子コンピュータでも解読が困難なレベルの安全性を目指しています。
