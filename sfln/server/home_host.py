import os
import subprocess
import time
import sys

def run_home_server():
    print("===============================================")
    print("   SFLN ホームホスティング・アシスタント (Easy Mode) ")
    print("===============================================")
    print("VPSや難しい設定は不要です！このスクリプトだけで、")
    print("あなたのPCを世界中からアクセス可能なリレーサーバーにできます。")
    print("-----------------------------------------------")
    print("[✓] GitHub利用規約 (TOS) に完全準拠しています")
    print("[✓] ルーターのポート開放設定は一切不要です")
    print("[✓] Cloudflareによる強力なセキュリティ保護が適用されます")
    print("-----------------------------------------------")

    # 1. Start SFLN Server in background
    print("> SFLN サーバーを起動しています...")
    server_process = subprocess.Popen([sys.executable, "sfln/server/main.py"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True)

    # 2. Check for cloudflared
    try:
        subprocess.run(["cloudflared", "--version"], check=True, capture_output=True)
    except:
        print("エラー: 'cloudflared' が見つかりませんでした。")
        print("以下のURLからインストールしてください:")
        print("https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/install-run/")
        server_process.kill()
        return

    # 3. Start Tunnel
    print("> 安全なトンネルを開設しています (localhost:9001)...")
    tunnel_process = subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:9001"],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     text=True)

    print("\n--- 次のステップ ---")
    print("1. 下に 'trycloudflare.com' を含むリンクが表示されるまで待ってください。")
    print("2. そのリンクをコピーして、f5.si の CNAME レコードに設定してください。")
    print("3. これで、あなたのサーバーが世界中に公開されます！")
    print("-----------------------------------------------\n")

    try:
        while True:
            line = tunnel_process.stdout.readline()
            if not line: break
            if "trycloudflare.com" in line:
                print(f"!!! 公開用リレー URL: {line.strip()} !!!")
            sys.stdout.write(line)
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n> シャットダウンしています...")
        tunnel_process.kill()
        server_process.kill()

if __name__ == "__main__":
    run_home_server()
