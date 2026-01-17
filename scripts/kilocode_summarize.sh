#!/bin/bash
# Kilo Code CLI を使った要約バッチ処理スクリプト
# 
# 使用方法:
#   ./scripts/kilocode_summarize.sh [オプション]
#
# オプション:
#   --all           すべての_cleaned.txtファイルを処理
#   --file FILE     特定のファイルのみ処理
#   --dry-run       実際の実行をスキップ（コマンドの確認のみ）
#
# 前提条件:
#   - Kilo Code CLIがインストール済みであること
#   - data/transcripts/ に _cleaned.txt と _description.txt が存在すること

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

TRANSCRIPT_DIR="${PROJECT_ROOT}/data/transcripts"
SUMMARY_DIR="${PROJECT_ROOT}/data/summaries"
SYSTEM_PROMPT="${PROJECT_ROOT}/blog_article_system.txt"

# 出力ディレクトリがなければ作成
mkdir -p "$SUMMARY_DIR"

# デフォルト設定
DRY_RUN=false
PROCESS_ALL=false
SINGLE_FILE=""
SLEEP_SECONDS=5

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            PROCESS_ALL=true
            shift
            ;;
        --file)
            SINGLE_FILE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --sleep)
            SLEEP_SECONDS="$2"
            shift 2
            ;;
        *)
            echo "不明なオプション: $1"
            exit 1
            ;;
    esac
done

# ファイル処理関数
process_file() {
    local transcript_file="$1"
    local video_id
    video_id=$(basename "$transcript_file" | sed 's/_cleaned.txt//')
    
    local desc_file="${TRANSCRIPT_DIR}/${video_id}_description.txt"
    local output_file="${SUMMARY_DIR}/${video_id}_summary.md"
    
    echo "=== 処理中: $video_id ==="
    
    # 概要欄ファイルの存在確認
    if [[ ! -f "$desc_file" ]]; then
        echo "  ⚠️ 概要欄ファイルが存在しません: $desc_file"
        echo "  → process_video.py --provider kilocode で概要欄を取得してください"
        return 1
    fi
    
    # 既存の要約をスキップするかどうか確認
    if [[ -f "$output_file" ]]; then
        echo "  ⚠️ 要約ファイルが既に存在します: $output_file"
        echo "  → スキップします（上書きする場合は手動で削除してください）"
        return 0
    fi
    
    # Kilo Code CLI コマンドを構築
    local cmd="kilocode --auto \"システムプロンプト@${SYSTEM_PROMPT} に従い、動画概要欄 @${desc_file} と 文字起こし @${transcript_file} を日本語で要約し、@${output_file} として書き出してください。\""
    
    if $DRY_RUN; then
        echo "  [dry-run] 実行予定コマンド:"
        echo "    $cmd"
    else
        echo "  実行中..."
        eval "$cmd"
        echo "  ✓ 完了: $output_file"
    fi
    
    return 0
}

# メイン処理
if [[ -n "$SINGLE_FILE" ]]; then
    # 特定ファイルのみ処理
    if [[ ! -f "$SINGLE_FILE" ]]; then
        echo "エラー: ファイルが見つかりません: $SINGLE_FILE"
        exit 1
    fi
    process_file "$SINGLE_FILE"
elif $PROCESS_ALL; then
    # すべてのファイルを処理
    count=0
    for transcript_file in "$TRANSCRIPT_DIR"/*_cleaned.txt; do
        if [[ -f "$transcript_file" ]]; then
            process_file "$transcript_file"
            count=$((count + 1))
            
            # 最後のファイル以外はスリープ
            if ! $DRY_RUN; then
                echo "  ⏳ ${SLEEP_SECONDS}秒待機..."
                sleep "$SLEEP_SECONDS"
            fi
        fi
    done
    echo ""
    echo "=== 完了 ==="
    echo "処理したファイル数: $count"
else
    echo "使用方法:"
    echo "  $0 --all              すべてのファイルを処理"
    echo "  $0 --file FILE        特定のファイルを処理"
    echo "  $0 --dry-run --all    ドライラン（コマンド確認のみ）"
    echo ""
    echo "利用可能なファイル:"
    ls -1 "$TRANSCRIPT_DIR"/*_cleaned.txt 2>/dev/null | head -10 || echo "  ファイルがありません"
fi
