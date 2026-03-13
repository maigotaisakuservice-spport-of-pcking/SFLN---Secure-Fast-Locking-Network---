import os
import subprocess
import time
import sys

def run_home_server():
    print("--- SFLN Home Hosting Assistant ---")
    print("This script will help you start the server and expose it via Cloudflare.")

    # 1. Start SFLN Server in background
    print("> Starting SFLN Server...")
    server_process = subprocess.Popen([sys.executable, "sfln/server/main.py"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True)

    # 2. Check for cloudflared
    try:
        subprocess.run(["cloudflared", "--version"], check=True, capture_output=True)
    except:
        print("Error: 'cloudflared' not found. Please install it first from:")
        print("https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/install-run/")
        server_process.kill()
        return

    # 3. Start Tunnel
    print("> Opening Secure Tunnel to localhost:9001...")
    tunnel_process = subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:9001"],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     text=True)

    print("\n--- ACTION REQUIRED ---")
    print("Wait for the 'trycloudflare.com' link to appear below.")
    print("Copy that link and update your f5.si CNAME record.")
    print("------------------------\n")

    try:
        while True:
            line = tunnel_process.stdout.readline()
            if not line: break
            if "trycloudflare.com" in line:
                print(f"!!! YOUR PUBLIC RELAY URL: {line.strip()} !!!")
            sys.stdout.write(line)
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n> Shutting down...")
        tunnel_process.kill()
        server_process.kill()

if __name__ == "__main__":
    run_home_server()
