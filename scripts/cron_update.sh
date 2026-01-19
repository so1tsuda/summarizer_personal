#!/bin/bash
# Cron用自動更新スクリプト
# 3時間ごとに実行し、新着動画を処理してGitにプッシュ

set -e

# プロジェクトディレクトリ
cd "$(dirname "$0")/.."

# 仮想環境をアクティベート（必要に応じて）
# source .venv/bin/activate

# ログファイル
LOG_FILE="logs/cron_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

# Cron環境用のPATH設定 (Node.jsやuvを確実に見つけられるようにする)
export PATH="$HOME/.nvm/versions/node/v24.11.1/bin:$HOME/.local/bin:$PATH"

echo "=== Cron Update Started: $(date) ===" | tee -a "$LOG_FILE"

# 環境変数を読み込む (.envが存在する場合)
if [ -f .env ]; then
    echo "--- .envファイルを読み込み中 ---" | tee -a "$LOG_FILE"
    export $(grep -v '^#' .env | xargs)
fi

# プロバイダー設定 (引数があればそれを使い、なければgemini)
PROVIDER=${1:-"gemini"}
echo "Using provider: $PROVIDER" | tee -a "$LOG_FILE"

# RSS経由で新着動画を処理 (uv環境を使用)
uv run python3 scripts/batch_process_rss.py \
    --provider "$PROVIDER" \
    --days 3 \
    --min-duration 10 \
    --process-count 10 \
    --auto-commit \
    2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=$?

# Kilocodeプロバイダーの場合、文字起こし後に一括要約を実行
if [ $EXIT_CODE -eq 0 ] && [ "$PROVIDER" == "kilocode" ]; then
    echo "--- 🤖 Kilocode CLIによる要約を開始 ---" | tee -a "$LOG_FILE"
    bash scripts/kilocode_summarize.sh 2>&1 | tee -a "$LOG_FILE"
    KILO_EXIT_CODE=$?
    if [ $KILO_EXIT_CODE -ne 0 ]; then
        echo "❌ Kilocode要約に失敗しました" | tee -a "$LOG_FILE"
        EXIT_CODE=$KILO_EXIT_CODE
    fi
fi

# 成功した場合、Cloudflare Pagesにデプロイ
if [ $EXIT_CODE -eq 0 ]; then
    echo "--- 🚀 Cloudflare Pagesへの自動デプロイを開始 ---" | tee -a "$LOG_FILE"
    ./scripts/deploy.sh 2>&1 | tee -a "$LOG_FILE"
    DEPLOY_EXIT_CODE=$?
    if [ $DEPLOY_EXIT_CODE -ne 0 ]; then
        echo "❌ デプロイに失敗しました" | tee -a "$LOG_FILE"
        EXIT_CODE=$DEPLOY_EXIT_CODE
    fi
fi

echo "=== Cron Update Finished: $(date) (Exit: $EXIT_CODE) ===" | tee -a "$LOG_FILE"

# 古いログを削除（30日以上前）
find logs/ -name "cron_*.log" -mtime +30 -delete

exit $EXIT_CODE
