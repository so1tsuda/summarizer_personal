#!/bin/bash
# Linux NUC用 デプロイスクリプト
# 1. Next.jsをビルドして静的ファイルを生成 (out/)
# 2. Cloudflare Pagesにデプロイ

set -e

# プロジェクトディレクトリに移動
cd "$(dirname "$0")/.."

echo "--- 🛠️  Next.js Build 開始 ---"
npm run build

echo "--- 🚀 Cloudflare Pagesへデプロイ ---"
# wrangler.jsonの設定を使用してデプロイ
npx wrangler pages deploy out

echo "--- ✅ デプロイ完了 ---"
