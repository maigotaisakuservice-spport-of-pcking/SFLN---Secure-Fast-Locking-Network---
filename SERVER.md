# SFLN Service Server 運用ガイド

SFLN Service Server は、メッシュネットワークのバックボーンとして、クライアント間の通信リレーとピア情報の管理を行います。

## 1. サーバーの要件
- **OS**: Linux (Ubuntu 22.04+ 推奨) または Windows Server
- **Python**: 3.12+
- **ネットワーク**: 固定パブリックIPアドレス推奨。ポート 9000 (UDP) および 9001 (TCP/WS) の開放が必要です。

## 2. インストールとセットアップ

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

## 3. 運用に関する詳細

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
