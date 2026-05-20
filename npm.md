# SFLN JS SDK: NPM Package Creation Guide

SFLN JS SDK を NPM パッケージとして構築・公開する手順です。

## Automated Publishing (Recommended)
GitHub Actions により、バージョンタグ (`v*`) の Push 時に自動で NPM への公開が行われます。
1. `sfln/npm-library/package.json` のバージョンを更新します。
2. `v2.2.0` のようなタグを作成してリポジトリに Push します。
   ```bash
   git tag v2.2.0
   git push origin v2.2.0
   ```
3. GitHub Actions (`SFLN NPM Library Publish`) が自動的に起動し、`@sfln/library` を公開します。

## 1. ディレクトリ構成
本リポジトリでは `sfln/npm-library` がパッケージのソースディレクトリとして管理されています。
- `sfln.js`: コアロジック (Browser/Node.js 両対応)
- `package.json`: NPM メタデータ

## 2. package.json の構成 (例)
以下の設定を参考に `package.json` を編集します。

```json
{
  "name": "@sfln/sdk",
  "version": "2.2.0",
  "description": "Secure Fast Locking Network (SFLN) Web SDK",
  "main": "sfln.js",
  "exports": {
    ".": "./sfln.js",
    "./easy": "./sfln-easy.js"
  },
  "dependencies": {
    "ws": "^8.0.0"
  },
  "keywords": [
    "sfln",
    "p2p",
    "mesh",
    "vpn",
    "security"
  ],
  "author": "TekipakiPC",
  "license": "MIT"
}
```

## 3. Node.js 対応の確認 (`sfln.js`)
ブラウザと Node.js の両方で動作させるため、ライブラリ末尾に以下のエクスポート記述が含まれていることを確認してください。

```javascript
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SFLNCryptoJS, SFLNClientJS };
}
```

## 4. ビルド (Optional)
Web用とNode用にバンドルする場合は、Webpack や Rollup を使用します。

```bash
npm install --save-dev webpack webpack-cli
npx webpack ./sfln.js --output-filename sfln.min.js
```

## 5. 公開 (Publish)
NPM レジストリに公開します。

```bash
# 初回のみ
npm login

# 公開 (Scoped package の場合は --access public が必要)
npm publish --access public
```

## 6. 利用方法 (npm install)
利用側プロジェクトで以下を実行してインストールできます。

```bash
npm install @sfln/sdk
```
