# SFLN Service Server 運用ガイド

SFLN Service Server は、メッシュネットワークのバックボーンとして、クライアント間の通信リレーとピア情報の管理を行います。

## 1. サーバーの要件
- **OS**: Linux (Ubuntu 22.04+ 推奨) または Windows Server
- **Python**: 3.12+
- **ネットワーク**: 固定パブリックIPアドレス推奨。ポート 9000 (UDP) および 9001 (TCP/WS) の開放が必要です。

## 2. ホスティング環境の選択 (VPS vs レンタルサーバー)

SFLN サーバーを運用する場合、**VPS (Virtual Private Server)** の利用を強く推奨します。

### なぜ VPS なのか？
- **ポートの自由度**: SFLN は 9000 (UDP) や 9001 (TCP) を使用しますが、一般的なレンタルサーバー（共有サーバー）ではこれらの非標準ポートを開放できません。
- **常駐プログラムの実行**: 共有サーバーでは長時間稼働する Python プロセスが制限されることが多いですが、VPS は root 権限で systemd 等を用いて 24時間 安定稼働させることが可能です。
- **プロトコル制限の回避**: SFLN は独自の UDP 通信を使用します。レンタルサーバーの多くは HTTP/HTTPS (80/443) 以外のプロトコルを遮断しているため、SFLN の機能を十分に発揮できません。

### 比較まとめ
| 項目 | VPS (推奨) | レンタルサーバー (非推奨) |
| :--- | :--- | :--- |
| 自由度 | 高い (OS/root権限あり) | 低い (ファイル公開のみ) |
| SFLN 互換性 | **完全対応** | 動作困難 (ポート制限等) |
| 設定難易度 | 中程度 | 低い |
| 主な用途 | SFLN リレー/アプリサーバー | Webサイト/ブログ |

## 3. VPS が契約できない場合の代替案 (自宅 PC 運用)

VPS の契約が難しい場合、**自宅の PC をサーバー化して Cloudflare Tunnel で公開する** 方法がもっとも簡単で強力です。

### 3.1. 自宅 PC + Cloudflare Tunnel (無料)
GitHub Actions で使用している技術を自宅でも活用できます。
1. **サーバー起動**: 自分の PC で `python sfln/server/main.py` を実行。
2. **Cloudflared インストール**: [Cloudflare 公式](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/install-run/)からバイナリをダウンロード。
3. **トンネルの作成**: `cloudflared tunnel --url http://localhost:9001` を実行。
4. **ドメイン連携**: 発行された `trycloudflare.com` の URL を `f5.si` の CNAME に登録すれば完了です。
   - ※ ルーターのポート開放や固定 IP は一切不要です。
   - **一括起動スクリプト**: `python sfln/server/home_host.py` を実行すると、サーバーの起動とトンネルの確立を一度に行い、公開URLを表示します。

### 3.2. 無料クラウド枠の活用
以下のサービスには、クレジットカード登録が必要ですが、一生無料で使える VPS 枠があります。
- **Oracle Cloud (Always Free)**: ARM 4コア / 24GB メモリ。SFLN サーバーを動かすには十分すぎるスペックです。
- **Google Cloud (Always Free)**: e2-micro インスタンス。性能は低いですが、リレー用には使えます。

## 4. インストールとセットアップ

### 依存関係のインストール
```bash
pip install -r sfln/server/requirements.txt
```

### サーバーの起動
```bash
# 標準起動
python3 sfln/server/main.py

# 詳細ログを表示して起動
python3 sfln/server/main.py --log-level DEBUG
```

## 5. 運用に関する詳細

### ハイブリッド・リレー機能
このサーバーは、ネイティブアプリ用の **UDP (Port 9000)** と、ブラウザ用の **WebSocket (Port 9001)** の両方を同時に待ち受けます。異なるプロトコル間の通信も自動的にブリッジされます。

### 本番環境での永続化 (systemd)
Linux サーバーで 24/7 稼働させるには、`systemd` サービスとしての登録を推奨します。

```ini
[Unit]
Description=SFLN Service Server
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/sfln/server/main.py
Restart=always
User=sfln-user

[Install]
WantedBy=multi-user.target
```

### スケーリングとパフォーマンス
- **1GB/s ターゲット**: 大容量通信を支えるため、サーバーの帯域幅（Gbps級）と、OS の UDP 受信バッファの最適化が重要です。
- **セキュリティ**: サーバーは暗号化されたペイロードをそのまま転送するため、リレー内容を解読することはできません。
