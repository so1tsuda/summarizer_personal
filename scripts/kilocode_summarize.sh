#!/usr/bin/zsh
# Kilo Code CLI を使った要約バッチ処理スクリプト
# 
# 使用方法:
#   ./scripts/kilocode_summarize.sh [オプション]
#
# オプション:
#   --all           すべての_defuddle.md / _cleaned.txt ファイルを処理
#   --file FILE     特定のファイルのみ処理
#   --model MODEL   Kilo Code で使用するモデル (デフォルト: openrouter/z-ai/glm-5)
#   --dry-run       実際の実行をスキップ（コマンドの確認のみ）
#
# 前提条件:
#   - Kilo Code CLIがインストール済みであること
#   - jqがインストール済みであること (backlog処理用)
#   - data/transcripts/ に _defuddle.md または _cleaned.txt と _description.txt が存在すること (backlog以外の場合)

set -e

# 本スクリプトのディレクトリを取得
SCRIPT_DIR=${0:A:h}
PROJECT_ROOT=${SCRIPT_DIR:h}

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
PROCESS_BACKLOG=false
SINGLE_FILE=""
SLEEP_SECONDS=5
LIMIT_VAL=""
BACKLOG_FILE="data/backlog.json"
MODEL_NAME="${KILOCODE_MODEL:-openrouter/z-ai/glm-5}"

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            PROCESS_ALL=true
            shift
            ;;
        --backlog)
            PROCESS_BACKLOG=true
            shift
            ;;
        --file)
            SINGLE_FILE="$2"
            shift 2
            ;;
        --model)
            MODEL_NAME="$2"
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
if $PROCESS_ALL; then
    LIMIT=10000  # 実質的に無制限
elif [[ -n "$LIMIT_VAL" ]]; then
    LIMIT="$LIMIT_VAL"
else
    LIMIT=3
fi

# ファイル処理関数
process_file() {
    local transcript_file="$1"
    local video_id
    video_id=$(basename "$transcript_file")
    video_id=${video_id%_defuddle.md}
    video_id=${video_id%_cleaned.txt}
    
    local desc_file="${TRANSCRIPT_DIR}/${video_id}_description.txt"
    local output_file="${SUMMARY_DIR}/${video_id}.md"
    
    echo "=== 処理中: $video_id ==="
    
    # 概要欄ファイルの存在確認
    if [[ ! -f "$desc_file" ]]; then
        echo "  ⚠️ 概要欄ファイルが存在しません。取得を試みます..."
        
        # IPバン対策：10〜40秒のランダムな待機（YouTubeへのアクセスが発生するため）
        local delay=$((RANDOM % 31 + 10))
        echo "  ⏳ IPバン対策のため ${delay}秒待機します..."
        sleep "$delay"

        # IDがハイフンで始まる場合でも正しく渡すために -- を使用
        if uv run python3 scripts/process_video.py --provider kilocode -- "$video_id"; then
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

    # 文字起こしファイルの存在確認 (backlog経由の場合は transcription が必要)
    if [[ ! -f "$transcript_file" ]]; then
        echo "  ⚠️ 文字起こしファイルが存在しません。動画処理を実行します..."
        
        # IPバン対策：待機は process_video.py --provider kilocode 内部でも行われるが、念のため
        # process_video.py が すでに transcript を生成しているはず
        if [[ ! -f "$transcript_file" ]]; then
             # ここに来る場合は process_video.py --provider kilocode を再度呼ぶ
             # (概要欄取得時に呼ばれているはずだが、transcriptがない場合)
             uv run python3 scripts/process_video.py --provider kilocode -- "$video_id"
        fi

        if [[ ! -f "$transcript_file" ]]; then
            echo "  ❌ 文字起こしファイルの取得に失敗しました: $transcript_file"
            return 1
        fi
    fi
    
    # 検閲対象のキーワード（中国政治関連など、Kilocode/GLMでエラーになるもの）
    local SENSITIVE_KEYWORDS="(習近平|Xi Jinping|Xi Jingping|中国共産党|CCP|Chinese Communist Party|天安門|Tiananmen)"
    
    # 既存の要約をスキップするかどうか確認
    if [[ -f "$output_file" ]]; then
        echo "  ⚠️ 要約ファイルが既に存在します: $output_file"
        echo "  → スキップします（上書きする場合は手動で削除してください）"
        return 0
    fi

    # キーワードチェック（概要欄またはタイトルに検閲対象が含まれるか）
    local switch_to_gemini=false
    
    # 概要欄のチェック
    if [[ -f "$desc_file" ]]; then
        if grep -Ei "$SENSITIVE_KEYWORDS" "$desc_file" > /dev/null; then
            echo "  ⚠️ 概要欄に制限対象ワードを検出しました。Google Geminiに切り替えます。"
            switch_to_gemini=true
        fi
    fi
    
    # Kilo Code CLI または Gemini で処理
    if $switch_to_gemini; then
        if $DRY_RUN; then
            echo "  [dry-run] Geminiを実行予定: uv run python3 scripts/process_video.py --provider gemini -- \"$video_id\""
        else
            echo "  Geminiで要約を実行中..."
            if uv run python3 scripts/process_video.py --provider gemini -- "$video_id"; then
                echo "  ✓ Geminiでの要約が完了しました: $output_file"
            else
                echo "  ❌ Geminiでの要約に失敗しました。"
                return 1
            fi
        fi
    else
        # Kilo Code CLI コマンドを構築（パスは相対パスで指定）
        local prompt="システムプロンプト@${SYSTEM_PROMPT} に従い、動画概要欄 @${desc_file} と 文字起こし @${transcript_file} を日本語で要約し、@${output_file} として書き出してください。"
        local cmd
        if [[ -n "$MODEL_NAME" ]]; then
            cmd="kilocode -m ${MODEL_NAME} --auto \"${prompt}\""
        else
            cmd="kilocode --auto \"${prompt}\""
        fi
        
        if $DRY_RUN; then
            echo "  [dry-run] 実行予定コマンド:"
            echo "    $cmd"
        else
            echo "  実行中..."
            # kilocode実行時にエラー（政治的制限など）が出た場合のフォールバック
            if ! eval "$cmd"; then
                echo "  ⚠️ Kilocodeでエラーが発生しました。Geminiでのフォールバックを試みます..."
                if uv run python3 scripts/process_video.py --provider gemini -- "$video_id"; then
                    echo "  ✓ フォールバックによりGeminiで完了しました: $output_file"
                else
                    echo "  ❌ フォールバック実行も失敗しました。"
                    return 1
                fi
            else
                echo "  ✓ 完了: $output_file"
                
                # フロントマターの追加
                local json_file="${TRANSCRIPT_DIR}/${video_id}.json"
                if [[ -f "$json_file" ]]; then
                    echo "  📝 フロントマターを追加中..."
                    local title channel published_at
                    title=$(jq -r '.title' "$json_file" | sed 's/"/\\"/g' | tr -d '\n')
                    channel=$(jq -r '.channel' "$json_file" | tr -d '\n')
                    published_at=$(jq -r '.published_at' "$json_file" | cut -c1-10)
                    
                    local temp_file=$(mktemp)
                    {
                        echo "---"
                        echo "title: \"$title\""
                        echo "video_id: \"$video_id\""
                        echo "channel: \"$channel\""
                        echo "published_at: \"$published_at\""
                        echo "youtube_url: \"https://www.youtube.com/watch?v=$video_id\""
                        echo "thumbnail: \"https://i.ytimg.com/vi/$video_id/hqdefault.jpg\""
                        echo "summarized_at: \"$(date -Iseconds)\""
                        if [[ -n "$MODEL_NAME" ]]; then
                            echo "model: \"$MODEL_NAME\""
                        else
                            echo "model: \"kilocode\""
                        fi
                        echo "---"
                        echo ""
                        cat "$output_file"
                    } > "$temp_file"
                    mv "$temp_file" "$output_file"
                    echo "  ✓ フロントマターを追加しました。"
                else
                    echo "  ⚠️ JSONファイルが見つからないため、フロントマターの追加をスキップします: $json_file"
                fi
            fi
        fi
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
elif $PROCESS_BACKLOG; then
    # backlog.json から未処理の動画を処理
    if [[ ! -f "$BACKLOG_FILE" ]]; then
        echo "エラー: バックログファイルが見つかりません: $BACKLOG_FILE"
        exit 1
    fi

    echo "=== バックログから動画を取得中 (制限: $LIMIT) ==="
    
    # 処理済み動画を一度クリーンアップ
    python3 scripts/manage_backlog.py --clean

    # jq を使って video_id を取得。
    video_ids=($(jq -r ".queue[0:$LIMIT] | .[].video_id" "$BACKLOG_FILE"))
    
    if [[ ${#video_ids[@]} -eq 0 ]]; then
        echo "バックログに処理待ちの動画はありません。"
        exit 0
    fi

    processed_count=0
    for video_id in "${video_ids[@]}"; do
        transcript_file="${TRANSCRIPT_DIR}/${video_id}_defuddle.md"
        if [[ ! -f "$transcript_file" ]]; then
            transcript_file="${TRANSCRIPT_DIR}/${video_id}_cleaned.txt"
        fi
        if process_file "$transcript_file"; then
            processed_count=$((processed_count + 1))
            # バックログから削除
            python3 scripts/manage_backlog.py --remove "$video_id" > /dev/null 2>&1
        elif [[ $? -eq 0 ]]; then
            # すでに存在してスキップされた場合なども削除
            python3 scripts/manage_backlog.py --remove "$video_id" > /dev/null 2>&1
        fi
        
        # 連続処理時の短い待機
        if [[ $processed_count -lt ${#video_ids[@]} ]]; then
            sleep 2
        fi
    done

    echo ""
    echo "=== 完了 ==="
    echo "処理を試みた動画数: ${#video_ids[@]}"
    echo "新規処理した動画数: $processed_count"
else
    # ファイルを処理（デフォルトは3つまで、--allなら無制限）
    count=0
    processed_count=0
    typeset -A seen_video_ids
    
    # defuddle Markdown を優先しつつ、更新日時が新しい順に処理
    for transcript_file in $(ls -t "$TRANSCRIPT_DIR"/*_defuddle.md "$TRANSCRIPT_DIR"/*_cleaned.txt 2>/dev/null); do
        if [[ -f "$transcript_file" ]]; then
            video_id=$(basename "$transcript_file")
            video_id=${video_id%_defuddle.md}
            video_id=${video_id%_cleaned.txt}

            if [[ -n "${seen_video_ids[$video_id]}" ]]; then
                continue
            fi
            seen_video_ids[$video_id]=1

            # すでに要約があるかチェック（カウント対象外にするため）
            output_file="${SUMMARY_DIR}/${video_id}.md"
            
            if [[ ! -f "$output_file" ]]; then
                if process_file "$transcript_file"; then
                    processed_count=$((processed_count + 1))
                fi
                
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
