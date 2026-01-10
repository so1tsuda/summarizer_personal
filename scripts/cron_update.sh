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

echo "=== Cron Update Started: $(date) ===" | tee -a "$LOG_FILE"

# RSS経由で新着動画を処理
python3 scripts/batch_process_rss.py \
    --days 3 \
    --min-duration 10 \
    --max-videos 3 \
    --auto-commit \
    2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=$?

echo "=== Cron Update Finished: $(date) (Exit: $EXIT_CODE) ===" | tee -a "$LOG_FILE"

# 古いログを削除（30日以上前）
find logs/ -name "cron_*.log" -mtime +30 -delete

exit $EXIT_CODE
