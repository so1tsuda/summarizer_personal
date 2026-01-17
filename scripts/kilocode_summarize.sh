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

# 本スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 環境変数の読み込み (.envが存在する場合)
if [ -f "${PROJECT_ROOT}/.env" ]; then
    export $(grep -v '^#' "${PROJECT_ROOT}/.env" | xargs)
fi

# プロジェクトルートへ移動（相対パス指定のため）
cd "$PROJECT_ROOT"

# パス設定（PROJECT_ROOTへのcd後なので相対パスでOK）
TRANSCRIPT_DIR="data/transcripts"
SUMMARY_DIR="data/summaries"
SYSTEM_PROMPT="blog_article_system.txt"



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
        --limit)
            LIMIT_VAL="$2"
            shift 2
            ;;
        *)
            echo "不明なオプション: $1"
            exit 1
            ;;
    esac
done

# 引数で指定された制限を適用
if [[ -n "$LIMIT_VAL" ]]; then
    LIMIT="$LIMIT_VAL"
else
    LIMIT=3
fi

# ファイル処理関数
process_file() {
    local transcript_file="$1"
    local video_id
    video_id=$(basename "$transcript_file" | sed 's/_cleaned.txt//')
    
    local desc_file="${TRANSCRIPT_DIR}/${video_id}_description.txt"
    local output_file="${SUMMARY_DIR}/${video_id}.md"
    
    echo "=== 処理中: $video_id ==="
    
    # 概要欄ファイルの存在確認
    if [[ ! -f "$desc_file" ]]; then
        echo "  ⚠️ 概要欄ファイルが存在しません。取得を試みます..."
        
        # IDがハイフンで始まる場合でも正しく渡すために -- を使用
        if uv run python3 scripts/process_video.py --provider kilocode -- "$video_id" > /dev/null 2>&1; then
            echo "  ✅ 概要欄を取得しました。"
        else
            echo "  ❌ 概要欄の取得に失敗しました。video_id: $video_id"
            return 1
        fi
        
        # 再チェック
        if [[ ! -f "$desc_file" ]]; then
            echo "  ❌ 概要欄ファイルの生成が確認できませんでした: $desc_file"
            return 1
        fi
    fi
    
    # 既存の要約をスキップするかどうか確認
    if [[ -f "$output_file" ]]; then
        echo "  ⚠️ 要約ファイルが既に存在します: $output_file"
        echo "  → スキップします（上書きする場合は手動で削除してください）"
        return 0
    fi
    
    # Kilo Code CLI コマンドを構築（パスは相対パスで指定）
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
else
    # ファイルを処理（デフォルトは3つまで、--allなら無制限）
    count=0
    processed_count=0
    
    # ls -t で更新日時が新しい順に処理
    for transcript_file in $(ls -t "$TRANSCRIPT_DIR"/*_cleaned.txt 2>/dev/null); do
        if [[ -f "$transcript_file" ]]; then
            # すでに要約があるかチェック（カウント対象外にするため）
            video_id=$(basename "$transcript_file" | sed 's/_cleaned.txt//')
            output_file="${SUMMARY_DIR}/${video_id}.md"
            
            if [[ ! -f "$output_file" ]]; then
                # IPバン対策：10〜40秒のランダムな待機（ネットワークアクセスの可能性があるため）
                if [[ $processed_count -gt 0 ]] && ! $DRY_RUN; then
                    local delay=$((RANDOM % 31 + 10))
                    echo "⏳ IPバン対策のため ${delay}秒待機します..."
                    sleep "$delay"
                fi

                process_file "$transcript_file"
                processed_count=$((processed_count + 1))
                
                if [[ $processed_count -ge $LIMIT ]]; then
                    echo "目標処理数（$LIMIT件）に達したため終了します。"
                    break
                fi
                
                if ! $DRY_RUN; then
                    # ループの最後ではなく、各処理の冒頭で待機するように設計変更（失敗時も待機するため）
                    # ここでは何もしない
                    :
                fi
            fi
            count=$((count + 1))
        fi
    done
    echo ""
    echo "=== 完了 ==="
    echo "新規処理したファイル数: $processed_count"
fi
