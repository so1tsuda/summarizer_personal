# YouTube Summarizer (Personal)

長いYouTube動画を読みやすいブログ形式に要約するツールです。

## 🌟 特徴

- **RSS自動検出**: YouTube RSSフィードで新着動画を自動検出（API quota節約）
- **Gemini API**: Google AI Studio の無料枠で要約生成（コスト削減）
- **トピック特化の要約**: `blog_article` プロンプトにより、本質に絞った1500-2000字の凝縮された記事を生成
- **文字起こしクリーンアップ**: フィラー（「えー」「あの」）や言い淀みを自動除去し、トークン消費を抑制
- **日付別グループ化**: トップページに日付ごとの見出しを表示し、更新情報を整理
- **ページネーション**: 記事一覧に20件ごとのページ送り機能を追加
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

### 手動で1本の動画を処理 (標準: Gemini)

```bash
# 標準設定 (Gemini)
python scripts/process_video.py VIDEO_ID_OR_URL

# AIプロバイダーを指定 (Gemini or OpenRouter)
python scripts/process_video.py VIDEO_ID --provider openrouter --model anthropic/claude-3.5-sonnet
```

> [!NOTE]
> 文字起こしだけでなく、動画の**概要欄**も自動的に取得し、正確な人名（漢字）・企業名・番組情報の把握に活用しています。

### RSS経由で新着動画を一括処理（バックログ方式）

標準のワークフローです。複数のAIプロバイダーをサポートしています。

```bash
# 標準設定 (Gemini)
python scripts/batch_process_rss.py --days 7 --min-duration 10 --process-count 3

# OpenRouter経由の無料Geminiモデルを使用する場合
python scripts/batch_process_rss.py --provider openrouter --model google/gemini-2.0-flash-lite:free --process-count 3
```

**動作:**
1. RSSから新着動画を取得 → `data/backlog.json` のキューに追加
2. キューから古い順に指定個数取り出して処理
3. 処理済みは `data/state.json` に記録

オプション:
- `--days`: 何日前までの動画を取得するか（デフォルト: 7）
- `--min-duration`: 最小動画長（分、デフォルト: 10）
- `--provider`: AIプロバイダーを指定 (`gemini` or `openrouter`)
- `--model`: 使用するモデル名を指定
- `--process-count`: 一度に処理する動画数（デフォルト: 1）
- `--auto-commit`: 処理後に自動的にGit commit & push
- `--dry-run`: テスト実行（保存しない）

### バックログ管理

```bash
# キュー一覧を表示
python scripts/manage_backlog.py --list

# 過去動画をインポート（例: PIVOT の過去30日分）
python scripts/manage_backlog.py --import-channel UC8yHePe_RgUBE-waRWy6olw --days 30

# 手動で動画を追加
python scripts/manage_backlog.py --add VIDEO_ID

# 失敗した動画をリトライ
python scripts/manage_backlog.py --retry-failed
```

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
│   ├── state.json            # 処理済み動画の状態
│   └── backlog.json          # 処理待ちキュー
├── scripts/
│   ├── rss_fetch.py          # RSS経由で新着動画を取得
│   ├── process_video_gemini.py  # 単一動画を処理（Gemini版）
│   ├── batch_process_rss.py  # バックログ処理（RSS + Gemini）
│   ├── manage_backlog.py     # バックログ管理CLI
│   ├── text_cleanup.py       # 文字起こしクリーニング・整形ユーティリティ
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
