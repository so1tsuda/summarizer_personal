# YouTube Summarizer

YouTubeの長い動画を要約し、ブログ形式で読みやすいサイトにまとめる個人用ツールです。

## 📁 プロジェクト構成

```
summarizer_personal/
├── config/channels.csv           # 監視チャンネルリスト
├── data/
│   ├── transcripts/              # 文字起こしJSON
│   ├── summaries/                # 要約Markdown
│   └── state.json                # 処理済み動画管理
├── scripts/
│   ├── fetch_new_videos.py       # 新着動画取得
│   ├── process_video.py          # 単一動画処理
│   └── batch_process.py          # バッチ処理
├── src/                          # Next.js フロントエンド
└── out/                          # 静的ビルド出力
```

## 🛠️ セットアップ

### 1. 依存関係のインストール

```bash
# Python依存関係
pip install google-api-python-client youtube-transcript-api openai python-dotenv

# Node.js依存関係
npm install
```

### 2. APIキーの設定

`.env` ファイルをプロジェクトルートに作成:

```bash
YOUTUBE_API_KEY=your_youtube_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 3. チャンネルの登録

`config/channels.csv` にチャンネルを追加:

```csv
channel_id,channel_name,notes
UCxxxxxxxxxxxxxxxxxxxxxx,チャンネル名,メモ
```

## 🚀 使い方

### 単一動画を処理

```bash
# Video IDで処理
python scripts/process_video.py VIDEO_ID

# URLでも可
python scripts/process_video.py "https://www.youtube.com/watch?v=VIDEO_ID"

# ドライラン（保存せずテスト）
python scripts/process_video.py VIDEO_ID --dry-run
```

**出力:**
- `data/transcripts/{video_id}.json` - 文字起こし
- `data/summaries/{video_id}.md` - 要約

### 新着動画の確認

```bash
# 登録チャンネルの新着動画を確認
python scripts/fetch_new_videos.py

# 過去30日間、15分以上の動画を取得
python scripts/fetch_new_videos.py --days 30 --min-duration 15
```

### バッチ処理

```bash
# 過去7日間の新着動画を最大5件処理
python scripts/batch_process.py --days 7 --limit 5

# ドライラン
python scripts/batch_process.py --dry-run
```

## 💻 フロントエンド

### 開発サーバー

```bash
npm run dev
# → http://localhost:3000
```

### 静的ビルド

```bash
npm run build
# → out/ ディレクトリに静的ファイル生成
```

## ☁️ Cloudflare Pagesへのデプロイ

1. GitHubにリポジトリをプッシュ
2. Cloudflare Pages で新規プロジェクト作成
3. ビルド設定:
   - **Build command**: `npm run build`
   - **Build output directory**: `out`

## 📝 出力形式

### 文字起こし (JSON)

```json
{
  "video_id": "xxx",
  "title": "動画タイトル",
  "channel": "チャンネル名",
  "transcript": [
    {"start": 0.0, "duration": 2.5, "text": "こんにちは"}
  ]
}
```

### 要約 (Markdown)

```markdown
---
title: "動画タイトル"
video_id: "xxx"
channel: "チャンネル名"
published_at: "2026-01-10"
youtube_url: "https://www.youtube.com/watch?v=xxx"
thumbnail: "https://..."
---

## 要約

...
```

## 📄 License

Personal Use Only
