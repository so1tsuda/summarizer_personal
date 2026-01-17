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

## 🔧 セットアップ

### 1. 依存関係のインストール

```bash
# Python依存関係（uv推奨）
uv sync

# または従来のpip
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
GEMINI_API_KEY=your_google_ai_studio_api_key
```

- **YouTube API**: [Google Cloud Console](https://console.cloud.google.com/) で取得
- **Gemini API**: [Google AI Studio](https://aistudio.google.com/apikey) で取得（無料）

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

> [!TIP]
> 動画IDがハイフン（`-`）で始まる場合（例: `-NFqv6mTiPM`）、コマンドライン引数として正しく認識させるために `--` を使用してください：
> ```bash
> python scripts/process_video.py --provider kilocode -- -NFqv6mTiPM
> ```


> [!NOTE]
> 文字起こしだけでなく、動画の**概要欄**も自動的に取得し、正確な人名（漢字）・企業名・番組情報の把握に活用しています。

### RSS経由で新着動画を一括処理（バックログ方式）

標準のワークフローです。複数のAIプロバイダーをサポートしています。

```bash
# 標準設定 (Gemini)
python scripts/batch_process_rss.py --days 7 --min-duration 10 --process-count 3

# OpenRouter経由の無料Geminiモデルを使用する場合
python scripts/batch_process_rss.py --provider openrouter --model google/gemini-2.0-flash-lite:free --process-count 3

# Kilo Code CLI を使用する場合（APIキー不要、ローカルプロンプト連携）
# 詳細は「🤖 Kilo Code CLI ワークフロー」セクションを参照
python scripts/batch_process_rss.py --provider kilocode --process-count 3
```

**Kilo Code CLI 連携について:**
`--provider kilocode` を指定すると、文字起こしの取得と概要欄の保存のみを行い、LLMによる要約生成をスキップします。これにより、APIコストを抑えつつ、後述のワークフローで高品質な要約を生成できます。

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

## 🤖 Kilo Code CLI ワークフロー

Gemini API や OpenRouter API の代わりに、**[Kilo Code CLI](https://kilocode.com/)** を使用して要約を生成するワークフローです。APIキーを消費せず、プロジェクト内のシステムプロンプト（`blog_article_system.txt`）を最大限に活用した高品質な要約が可能です。

### ステップ 1: 動画情報と文字起こしの取得
まず、APIプロバイダーに `kilocode` を指定して、文字起こし（JSON）と概要欄（テキスト）を取得・保存します。この段階ではLLMによる要約は行われません。

```bash
# RSS経由で新着を取得する場合
python scripts/batch_process_rss.py --provider kilocode --process-count 3

# 特定の動画を1本取得する場合（IDがハイフンで始まる場合は -- を使用）
python scripts/process_video.py --provider kilocode -- -VIDEO_ID
```

### ステップ 2: Kilo Code による要約生成
保存されたデータを元に、Kilo Code CLI を呼び出して要約を生成します。

```bash
# 未要約のファイルを直近3件まで処理（デフォルト）
bash scripts/kilocode_summarize.sh

# 未要約の全ファイルを一括処理
bash scripts/kilocode_summarize.sh --all

# 処理件数を指定して実行
bash scripts/kilocode_summarize.sh --limit 5

# 特定のファイルのみ処理
bash scripts/kilocode_summarize.sh --file data/transcripts/VIDEO_ID_cleaned.txt
```

**このスクリプトがやっていること:**
- `blog_article_system.txt` をシステムプロンプトとして読み込みます。
- `data/transcripts/` 内の `_cleaned.txt`（文字起こし）と `_description.txt`（概要欄）を Kilo Code に渡します。
- 更新日時が新しい順に処理し、デフォルトでは最大3件まで処理を継続します。
- 生成された要約を `data/summaries/VIDEO_ID.md` として書き出します。

### 自動更新（Cron）での利用
`cron_update.sh` の引数に `kilocode` を渡すと、上記のステップ1とステップ2が連続して自動実行されます。詳細は「Cron自動実行」セクションを参照してください。


### Cron自動実行（3時間ごと）

```bash
# crontabを編集
crontab -e

# 以下を追加（3時間ごとに実行、標準: Gemini）
0 */3 * * * /home/so1/apps/summarizer_personal/scripts/cron_update.sh >> /home/so1/apps/summarizer_personal/logs/summarizer.log 2>&1

# Kilo Code CLI を使用して自動更新する場合
0 */3 * * * /home/so1/apps/summarizer_personal/scripts/cron_update.sh kilocode >> /home/so1/apps/summarizer_personal/logs/summarizer.log 2>&1
```

> [!TIP]
> `cron_update.sh` の引数に `kilocode` を渡すと、動画の取得・文字起こし保存に続いて、`kilocode_summarize.sh --all` が自動的に実行され、未要約の全ファイルが処理されます。

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
│   ├── process_video.py      # 単一動画を処理 (Gemini/OpenRouter)
│   ├── batch_process_rss.py  # バックログ処理 (RSS + AI)
│   ├── manage_backlog.py     # バックログ管理CLI
│   ├── deploy.sh             # NUC用デプロイスクリプト
│   ├── text_cleanup.py       # 文字起こしクリーンアップ
│   └── cron_update.sh        # Cron用自動更新スクリプト
├── src/                      # Next.js フロントエンド
├── gemini_summarizer.py      # Gemini API要約モジュール
├── openrouter_summarizer.py  # OpenRouter API要約モジュール
├── model_configs.json        # プロンプト設定
└── wrangler.json             # Cloudflare Pages設定

##  プロンプトのカスタマイズ

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

## 🌐 デプロイ (Cloudflare Pages)

Linux NUC から直接 Cloudflare Pages にデプロイし、高度なセキュリティで保護する構成です。

### 1. 手動デプロイ (NUC)

ビルドとアップロードを一括で行います。

```bash
# 初回のみログイン
npx wrangler login

# デプロイ実行
./scripts/deploy.sh
```

### 2. セキュリティ (Cloudflare Access)

サイト全体にパスワード（ログイン）制限をかけます。Cloudflare Zero Trust ダッシュボードから設定してください。

1. **Access -> Applications** でサイトを登録。
2. **Rules** で自分のメールアドレスのみ許可。
3. 指定したメールに届く認証コードを入力しないと、サイトを閲覧できなくなります。

> [!TIP]
> 静的サイトとしてエクスポートしているため、サイト表示にサーバー費用は発生しません。

## � ライセンス

Personal Use Only
