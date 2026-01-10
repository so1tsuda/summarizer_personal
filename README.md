# YouTube Summarizer (Personal)

長いYouTube動画を読みやすいブログ形式に要約するツールです。

## 🌟 特徴

- **RSS自動検出**: YouTube RSSフィードで新着動画を自動検出（API quota節約）
- **Gemini API**: Google AI Studio の無料枠で要約生成（コスト削減）
- **自動デプロイ**: Cron → Git Push → Cloudflare Pages で完全自動化
- **埋め込み動画**: 記事ページで直接YouTube視聴可能
- **文字起こしコピー**: タイムスタンプ付き全文を1クリックでコピー

## � セットアップ

### 1. 依存関係のインストール

```bash
# Python依存関係
pip install -r requirements.txt

# Node.js依存関係（フロントエンド）
npm install
```

### 2. API キーの設定

`.env` ファイルを作成:

```bash
cp .env.example .env
```

以下のAPIキーを設定:

```
YOUTUBE_API_KEY=your_youtube_api_key
GOOGLE_AI_API_KEY=your_google_ai_studio_api_key
```

- **YouTube API**: [Google Cloud Console](https://console.cloud.google.com/) で取得
- **Google AI API**: [Google AI Studio](https://aistudio.google.com/apikey) で取得（無料）

### 3. チャンネル登録

`config/channels.csv` にチャンネルを追加:

```csv
channel_id,channel_name,notes
UCxxxxxx,チャンネル名,メモ（任意）
```

## 🚀 使い方

### 手動で1本の動画を処理

```bash
python scripts/process_video_gemini.py VIDEO_ID_OR_URL
```

### RSS経由で新着動画を一括処理

```bash
python scripts/batch_process_rss.py --days 7 --min-duration 10
```

オプション:
- `--days`: 何日前までの動画を取得するか（デフォルト: 7）
- `--min-duration`: 最小動画長（分、デフォルト: 10）
- `--max-videos`: 一度に処理する最大動画数（デフォルト: 5）
- `--auto-commit`: 処理後に自動的にGit commit & push
- `--dry-run`: テスト実行（保存しない）

### Cron自動実行（3時間ごと）

```bash
# crontabを編集
crontab -e

# 以下を追加（3時間ごとに実行）
0 */3 * * * /path/to/summarizer_personal/scripts/cron_update.sh >> /var/log/summarizer.log 2>&1
```

## 🎨 フロントエンド

### 開発サーバー

```bash
npm run dev
```

http://localhost:3000 でアクセス

### ビルド（Cloudflare Pages用）

```bash
npm run build
```

`out/` ディレクトリに静的ファイルが生成されます。

## 📁 ディレクトリ構造

```
.
├── config/
│   └── channels.csv          # 登録チャンネル
├── data/
│   ├── summaries/            # 要約記事（Markdown）
│   ├── transcripts/          # 文字起こし（JSON）
│   └── state.json            # 処理済み動画の状態
├── scripts/
│   ├── rss_fetch.py          # RSS経由で新着動画を取得
│   ├── process_video_gemini.py  # 単一動画を処理（Gemini版）
│   ├── batch_process_rss.py  # 一括処理（RSS + Gemini）
│   └── cron_update.sh        # Cron用自動更新スクリプト
├── src/                      # Next.js フロントエンド
├── gemini_summarizer.py      # Gemini API要約モジュール
└── model_configs.json        # プロンプト設定
```

## � プロンプトのカスタマイズ

`model_configs.json` でプロンプトテンプレートを編集:

```json
{
  "prompt_templates": {
    "blog_article": {
      "system_message": "...",
      "tone_instructions": [...],
      "output_instructions": [...]
    }
  }
}
```

## 📊 Gemini API 無料枠

| 項目 | 制限 |
|------|------|
| リクエスト/分 | 10 RPM |
| リクエスト/日 | 250 RPD |
| トークン/分 | 250,000 TPM |

`batch_process_rss.py` は自動的に6秒間隔でリクエストを送信します（10 RPM対応）。

## 🌐 デプロイ（Cloudflare Pages）

1. GitHubリポジトリをCloudflare Pagesに接続
2. ビルド設定:
   - **Build command**: `npm run build`
   - **Build output directory**: `out`
3. Cron → Git Push で自動デプロイ

## � ライセンス

Personal Use Only
