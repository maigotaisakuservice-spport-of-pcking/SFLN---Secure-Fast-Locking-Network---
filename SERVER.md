# SFLN Service Server 運用ガイド

SFLN Service Server は、メッシュネットワークのバックボーンとして、クライアント間の通信リレーとピア情報の管理を行います。

> [!IMPORTANT]
> **自宅ホスティング (Linux推奨) のススメ**
> 現在の推奨構成は、自宅の Linux サーバー (Ubuntu等) を使用したホスティングです。
> `sfln/server/home_host.py` スクリプトを使用することで、複雑なネットワーク設定なしで安全にサーバーを公開できます。

> [!CAUTION]
> **GitHub Actions での運用に関する重要事項**
> リポジトリに含まれる `sfln-server.yml` は、**一時的な機能テストおよびデモ（CI/CDの一環）のみ**を目的としています。
> GitHub Actions を常時稼働のリレーサーバーとして利用することは、**GitHub の利用規約 (TOS) に違反する可能性が高い**ため、本番運用には絶対に使用しないでください。
> 本番環境や長時間の運用には、必ず後述の **VPS** または **自宅ホスト (`home_host.py`)** を利用してください。

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

## 3. VPS が契約できない場合の代替案 (自宅 Linux 運用 - 推奨)

VPS の契約が難しい場合、**自宅の Linux PC (Ubuntu, Debian, Raspberry Pi等) をサーバー化して Cloudflare Tunnel で公開する** 方法がもっとも簡単で強力です。

### 3.1. 自宅 Linux + Cloudflare Tunnel (無料・ポート開放不要)
GitHub Actions で使用している技術を自宅でも活用できます。
1. **サーバー準備**: 古い PC や Raspberry Pi に Linux (Ubuntu 推奨) をインストールします。
2. **Cloudflared インストール**:
   ```bash
   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared.deb
   ```
3. **SFLN サーバー起動**: `python3 sfln/server/main.py` を実行。
4. **トンネルの作成**: `cloudflared tunnel --url http://localhost:9001` を実行。
4. **ドメイン連携**: 発行された `trycloudflare.com` の URL を `f5.si` の CNAME に登録すれば完了です。
   - ※ ルーターのポート開放や固定 IP は一切不要です。
   - **一括起動スクリプト**: `python sfln/server/home_host.py` を実行すると、サーバーの起動とトンネルの確立を一度に行い、公開URLを表示します。
   - **安全性**: この方法はあなたの PC のリソースを使用するため、GitHub の TOS 制限を受けることなく、安全にサービスを提供できます。

### 3.2. 推奨 VPS プロバイダー
以下のサービスは、SFLN サーバーの運用に必要な「固定IP」「全ポート開放」「root権限」を備えた VPS を提供しています。

- **DigitalOcean (もっともおすすめ)**:
    - **メリット**: 設定が非常に簡単で、初心者でも 1分 でサーバーを立てられます。
    - **特典**: 新規登録で **$200 分の無料クレジット (60日間有効)** がもらえることが多く、初期費用なしで最強スペックを試せます。
    - **相性**: Python 3.12+ の公式サポートがあり、SFLN サーバーとの相性が抜群です。
- **Oracle Cloud (Always Free)**:
    - **メリット**: 性能が非常に高い（ARM 4コア/24GBメモリ）サーバーが **一生無料**。
    - **デメリット**: 登録時のクレジットカード審査が厳しく、アカウント作成で弾かれることがあります。
- **Google Cloud (Always Free)**:
    - **メリット**: 信頼性が高い。
    - **デメリット**: 無料枠（e2-micro）は性能が低いため、大量の通信リレーには不向きです。

## 4. あなたにぴったりの構成は？ (診断ガイド)

どれを使うか迷っている場合は、以下の基準で選んでみてください。

1. **「とりあえず今すぐ、1円も払わずに試したい」**
    - 👉 **自宅ホスト (`home_host.py`)** を使いましょう。一番簡単で、TOS違反の心配もありません。
2. **「本格的なサーバーが欲しいけど、設定が難しそう」**
    - 👉 **DigitalOcean** の $200 クレジットを使って Droplet を立てましょう。UIが分かりやすく、SFLN の設定もスムーズです。
3. **「一度設定したら、ずっと無料で使い続けたい」**
    - 👉 **Oracle Cloud** の Always Free に挑戦しましょう。登録さえできれば最強の環境が手に入ります。

## 5. インストールとセットアップ

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

## 6. 運用に関する詳細

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
