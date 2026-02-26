# SFLN GUI Client Build Instructions

SFLN GUIクライアントを Windows または Linux 用の実行ファイル (.exe / binary) としてビルドする手順です。

## 1. 事前準備
Python 3.10以上がインストールされていることを確認してください。

ビルドに必要なライブラリをインストールします：
```bash
pip install PySide6 psutil cryptography pyinstaller
```

## 2. ビルド手順

### Windows の場合
コマンドプロンプトまたは PowerShell を開き、以下のコマンドを実行します：
```bash
pyinstaller --noconsole --onefile --name SFLN-Client sfln/client/gui.py
```
ビルドが完了すると、`dist/SFLN-Client.exe` が生成されます。

### Linux の場合
ターミナルを開き、以下のコマンドを実行します：
```bash
pyinstaller --noconsole --onefile --name SFLN-Client sfln/client/gui.py
```
ビルドが完了すると、`dist/SFLN-Client` 実行ファイルが生成されます。

## 3. 注意事項
- **管理者権限**: アプリ一覧の取得やネットワーク制御のため、実行時は管理者権限（Windows: 管理者として実行, Linux: sudo）が必要な場合があります。
- **暗号化ライブラリ**: `cryptography` ライブラリのバイナリが正しく同梱されるよう、最新の PyInstaller を使用してください。
