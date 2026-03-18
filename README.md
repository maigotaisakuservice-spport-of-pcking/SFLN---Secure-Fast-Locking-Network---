# SFLN (Secure-Fast-Locking-Network) Project

[日本語](#japanese) | [English](#english)

---

<a name="japanese"></a>
# 日本語ガイド

SFLN は、12,000桁暗号と 1GB/s ターゲットを両立させた次世代 P2P メッシュネットワークです。独自規格 **SFLN-P v2** を採用し、企業向けの高度なセキュリティと圧倒的な転送速度を提供します。

## 📱 クライアント・アプリケーション

一般利用者およびシステム管理者向けの多機能クライアントです。

### 🛡️ 特徴とインストール
- **常駐機能**: 起動後はシステムトレイに格納され、24時間バックグラウンドでネットワークを保護します。
- **管理者権限 (Admin)**: ネットワークスタックの最適化とパケット制御のため、必ず管理者権限（Windows: 管理者として実行, Linux: sudo）で実行してください。
- **自動起動**: 設定画面から OS 起動時の自動実行を登録可能です。
- **ペアリング**: Node ID または QR コードで相手とペアリング。エッジAIが最適な経路（直接 P2P またはサーバーリレー）を自動判別します。

## ⚙️ SFLN-P v2 (独自プロトコル規格)
SFLN-P v2 は、RFC 準拠を目指すオープンな通信プロトコルです。
- **42バイト・バイナリヘッダー**: 高効率なパケット構造。
- **B+C 最適化**: ゼロコピー（B）とマルチプロセス並列処理（C）により 1GB/s を実現。
- **エンタープライズ対応**: ホワイトリスト制、ハードウェア指紋認証、監査ログ機能を標準装備。

## 🚀 開発者向け SDK
JavaScript/Node.js および Python に対応。`localhost:49000` のヘルスチェックにより、アプリの稼働状況を自動検証します。

---

<a name="english"></a>
# English Guide

SFLN is a next-generation P2P mesh network that balances 12,000-digit encryption with a 1GB/s throughput target. Utilizing the **SFLN-P v2** open standard, it provides enterprise-grade security and overwhelming transfer speeds.

## 📱 Client Application

A multi-functional client designed for both end-users and system administrators.

### 🛡️ Features & Installation
- **Resident Mode**: Minimized to the system tray, protecting your network 24/7 in the background.
- **Admin Privileges**: MUST be run as Administrator (Windows) or via `sudo` (Linux) for network stack optimization and packet control.
- **Auto-Startup**: Can be registered to run automatically on OS boot via settings.
- **Pairing**: Connect via Node ID or QR code. Edge AI automatically determines the optimal path (Direct P2P or Server Relay).

## ⚙️ SFLN-P v2 (Open Protocol Specification)
SFLN-P v2 is a decentralized communication protocol aiming for RFC compliance.
- **42-Byte Binary Header**: High-efficiency packet structure.
- **B+C Optimization**: Zero-copy (Principle B) and Multi-process parallelism (Principle C) to reach 1GB/s.
- **Enterprise Ready**: Includes Whitelisting, Hardware Fingerprinting, and Audit Logging by default.

## 🚀 Developer SDK
Supports JavaScript/Node.js and Python. Automatically verifies the local app status via a health check on `localhost:49000`.

---
**Author:** TekipakiPC
**Copyright:** © 2025 SFLN Project. All Rights Reserved.
