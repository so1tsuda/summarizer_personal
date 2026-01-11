#!/bin/bash
# process_video_claude.sh
# Claude Code CLIを使用した記事生成スクリプト
#
# 使用例:
#   ./scripts/process_video_claude.sh VIDEO_ID
#   ./scripts/process_video_claude.sh https://www.youtube.com/watch?v=VIDEO_ID

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 引数チェック
if [ -z "$1" ]; then
    echo "Usage: $0 VIDEO_ID_OR_URL"
    echo ""
    echo "Options:"
    echo "  VIDEO_ID_OR_URL   YouTube video ID or URL"
    echo ""
    echo "Examples:"
    echo "  $0 dQw4w9WgXcQ"
    echo "  $0 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'"
    exit 1
fi

# VIDEO_IDを抽出
VIDEO_ID="$1"
if [[ "$VIDEO_ID" == *"youtube.com"* ]] || [[ "$VIDEO_ID" == *"youtu.be"* ]]; then
    VIDEO_ID=$(echo "$1" | grep -oP '(?<=v=|youtu.be/)[^&?]+' || echo "$1")
fi

echo "============================================================"
echo "Processing: $VIDEO_ID (Claude Code CLI)"
echo "============================================================"

TRANSCRIPT_PATH="data/transcripts/${VIDEO_ID}.json"
CLEANED_PATH="data/transcripts/${VIDEO_ID}_cleaned.txt"
SUMMARY_PATH="data/summaries/${VIDEO_ID}.md"

# 1. 文字起こしを取得（まだ無い場合）
if [ ! -f "$TRANSCRIPT_PATH" ]; then
    echo "📥 Fetching transcript..."
    python -c "
from scripts.process_video_gemini import get_transcript, save_transcript_json, get_video_info, load_api_keys
from googleapiclient.discovery import build
from pathlib import Path
import json

api_keys = load_api_keys()
youtube = build('youtube', 'v3', developerKey=api_keys.get('youtube_api_key'))
video_info = get_video_info(youtube, '$VIDEO_ID') or {}
transcript = get_transcript('$VIDEO_ID')
if transcript:
    save_transcript_json('$VIDEO_ID', video_info, transcript, Path('data/transcripts'))
    print(f'  ✓ Saved: $TRANSCRIPT_PATH')
else:
    print('  ✗ Failed to get transcript')
    exit(1)
"
fi

# 2. クリーンアップ済みテキストを生成（まだ無い場合）
if [ ! -f "$CLEANED_PATH" ]; then
    echo "🧹 Cleaning transcript..."
    python -c "
import json
from scripts.text_cleanup import clean_transcript_text, save_text_to_file

with open('$TRANSCRIPT_PATH', 'r', encoding='utf-8') as f:
    data = json.load(f)

if 'transcript' in data:
    raw_text = '\n'.join([item['text'] for item in data['transcript']])
else:
    raw_text = '\n'.join([item['text'] for item in data])

cleaned = clean_transcript_text(raw_text, keep_timestamps=False)
save_text_to_file(cleaned, '$CLEANED_PATH')
print(f'  ✓ Saved: $CLEANED_PATH')
"
fi

# 3. 動画情報を取得
echo "📋 Fetching video info..."
VIDEO_INFO=$(python -c "
import json
from scripts.process_video_gemini import get_video_info, load_api_keys
from googleapiclient.discovery import build

api_keys = load_api_keys()
youtube = build('youtube', 'v3', developerKey=api_keys.get('youtube_api_key'))
info = get_video_info(youtube, '$VIDEO_ID')
if info:
    print(json.dumps(info, ensure_ascii=False))
else:
    print('{}')
")

TITLE=$(echo "$VIDEO_INFO" | python -c "import sys, json; d=json.load(sys.stdin); print(d.get('title', 'Untitled'))")
CHANNEL=$(echo "$VIDEO_INFO" | python -c "import sys, json; d=json.load(sys.stdin); print(d.get('channel', 'Unknown'))")
PUBLISHED=$(echo "$VIDEO_INFO" | python -c "import sys, json; d=json.load(sys.stdin); print(d.get('published_at', '')[:10] if d.get('published_at') else '')")
THUMBNAIL="https://i.ytimg.com/vi/${VIDEO_ID}/hqdefault.jpg"

echo "  Title: $TITLE"
echo "  Channel: $CHANNEL"

# 4. Claude Code CLIで要約生成
echo "🤖 Generating summary with Claude Code..."

SUMMARY_CONTENT=$(cat "$CLEANED_PATH" | claude --system-prompt-file blog_article_system.txt -p "このstdinはYouTube文字起こしです。上の指示に厳密に従い、ブログ記事をMarkdownで出力してください。")

# 5. フロントマターを追加して保存
echo "💾 Saving summary..."
SUMMARIZED_AT=$(date -Iseconds)

cat > "$SUMMARY_PATH" << EOF
---
title: "$TITLE"
video_id: "$VIDEO_ID"
channel: "$CHANNEL"
published_at: "$PUBLISHED"
youtube_url: "https://www.youtube.com/watch?v=$VIDEO_ID"
thumbnail: "$THUMBNAIL"
summarized_at: "$SUMMARIZED_AT"
model: "claude-code"
---

$SUMMARY_CONTENT
EOF

echo "  ✓ Saved: $SUMMARY_PATH"

# 6. 状態ファイルを更新
python -c "
import json
from datetime import datetime

state_path = 'data/state.json'
try:
    with open(state_path, 'r', encoding='utf-8') as f:
        state = json.load(f)
except:
    state = {'processed_videos': {}}

state['processed_videos']['$VIDEO_ID'] = {
    'title': '''$TITLE''',
    'channel': '$CHANNEL',
    'processed_at': datetime.now().isoformat(),
    'model': 'claude-code'
}

with open(state_path, 'w', encoding='utf-8') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
print('  ✓ State updated')
"

echo ""
echo "============================================================"
echo "✅ Done! Article saved to: $SUMMARY_PATH"
echo "============================================================"
