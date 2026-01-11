#!/usr/bin/env python3
"""
単一の動画を処理するスクリプト (Gemini API版)
- 文字起こしを取得してJSONに保存
- Google Gemini APIを使って要約
- 要約をMarkdownに保存
- 処理状態を更新
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gemini_summarizer import GeminiSummarizer, load_api_key as load_gemini_key
from openrouter_summarizer import OpenRouterSummarizer
from scripts.text_cleanup import clean_transcript_text, get_cleaned_path, save_text_to_file


def load_api_keys():
    """環境変数からAPIキーを読み込む"""
    try:
        from dotenv import load_dotenv
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass
    
    return {
        "youtube_api_key": os.getenv("YOUTUBE_API_KEY", ""),
        "google_ai_api_key": os.getenv("GOOGLE_AI_API_KEY", ""),
    }


def get_video_info(youtube, video_id: str) -> Dict:
    """YouTube動画の基本情報を取得"""
    try:
        response = youtube.videos().list(
            part='snippet,contentDetails',
            id=video_id
        ).execute()
        
        if not response.get('items'):
            raise ValueError(f"動画が見つかりません: {video_id}")
        
        video = response['items'][0]
        snippet = video['snippet']
        
        return {
            'title': snippet['title'],
            'channel': snippet['channelTitle'],
            'published_at': snippet['publishedAt'],
            'duration': video['contentDetails']['duration'],
            'thumbnail': snippet['thumbnails'].get('high', {}).get('url', ''),
            'description': snippet.get('description', ''),
        }
    except HttpError as e:
        raise Exception(f"YouTube APIエラー: {e}")


def get_transcript(video_id: str) -> list:
    """文字起こしを取得"""
    try:
        print(f"字幕を取得中 (ID: {video_id})...")
        
        languages = ['ja', 'en', 'en-US', 'en-GB']
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        
        try:
            transcript_obj = transcript_list.find_manually_created_transcript(languages)
            print(f"  手動字幕が見つかりました: {transcript_obj.language}")
        except:
            try:
                transcript_obj = transcript_list.find_generated_transcript(languages)
                print(f"  自動字幕が見つかりました: {transcript_obj.language}")
            except:
                transcript_obj = next(iter(transcript_list))
                print(f"  利用可能な最初の字幕を使用します: {transcript_obj.language}")
        
        transcript = transcript_obj.fetch()
        
        formatted_transcript = []
        for entry in transcript:
            formatted_transcript.append({
                'start': entry.start,
                'duration': entry.duration,
                'text': entry.text.strip()
            })
        
        print(f"  文字起こし完了: {len(formatted_transcript)}行")
        return formatted_transcript
    
    except Exception as e:
        print(f"文字起こしの取得に失敗しました: {e}")
        return []


def save_transcript_json(video_id: str, video_info: Dict, transcript: list, output_dir: Path) -> Path:
    """文字起こしをJSONファイルに保存"""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_id}.json"
    
    data = {
        "video_id": video_id,
        "title": video_info.get("title", ""),
        "channel": video_info.get("channel", ""),
        "published_at": video_info.get("published_at", ""),
        "duration": video_info.get("duration", ""),
        "thumbnail": video_info.get("thumbnail", ""),
        "fetched_at": datetime.now().isoformat(),
        "transcript": transcript,
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_path


def save_summary_markdown(video_id: str, video_info: Dict, summary: str, output_dir: Path, model_name: str = "gemini") -> Path:
    """要約をMarkdownファイルに保存"""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_id}.md"
    
    escaped_title = video_info.get('title', '').replace('"', '\\"')
    published_date = video_info.get('published_at', '')[:10]
    
    frontmatter = f"""---
title: "{escaped_title}"
video_id: "{video_id}"
channel: "{video_info.get('channel', '')}"
published_at: "{published_date}"
youtube_url: "https://www.youtube.com/watch?v={video_id}"
thumbnail: "{video_info.get('thumbnail', '')}"
summarized_at: "{datetime.now().isoformat()}"
model: "{model_name}"
---

"""
    
    content = frontmatter + summary
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return output_path


def update_state(state_path: Path, video_id: str, video_info: Dict):
    """処理状態を更新"""
    if state_path.exists():
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {"processed_videos": {}}
    
    state["processed_videos"][video_id] = {
        "processed_at": datetime.now().isoformat(),
        "title": video_info.get("title", ""),
        "channel": video_info.get("channel", ""),
    }
    
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def process_video(
    video_id: str,
    youtube,
    summarizer: GeminiSummarizer,
    transcripts_dir: Path,
    summaries_dir: Path,
    state_path: Path,
    dry_run: bool = False
) -> Dict:
    """動画を処理"""
    print(f"処理開始: {video_id}")
    
    # 1. 動画情報を取得
    print("  動画情報を取得中...")
    video_info = get_video_info(youtube, video_id)
    print(f"  タイトル: {video_info['title']}")
    print(f"  チャンネル: {video_info['channel']}")
    
    # 2. 文字起こしを取得
    print("  文字起こしを取得中...")
    transcript = get_transcript(video_id)
    
    if not transcript:
        raise ValueError("文字起こしが取得できませんでした")
    
    # 3. JSONに保存
    if not dry_run:
        transcript_path = save_transcript_json(video_id, video_info, transcript, transcripts_dir)
        print(f"  文字起こし保存: {transcript_path}")
    else:
        print("  [dry-run] 文字起こし保存をスキップ")
    
    # 4. 要約を生成
    print(f"  要約を生成中 (Gemini {summarizer.model_name})...")
    
    if not dry_run:
        # トークン節約のためにクリーンアップ
        raw_transcript_text = "\n".join([f"[{item['start']:.1f}] {item['text']}" for item in transcript])
        cleaned_transcript_text = clean_transcript_text(raw_transcript_text, keep_timestamps=False)
        
        # クリーンアップ済みテキストを保存
        cleaned_path = get_cleaned_path(str(transcript_path))
        save_text_to_file(cleaned_transcript_text, cleaned_path)
        print(f"  ✓ クリーンアップ済みテキスト保存: {cleaned_path}")
        
        # クリーンアップ済みテキストをLLMに送る
        summary, metadata = summarizer.generate_summary(cleaned_transcript_text, video_info.get('description', ''))
        print(f"  要約完了: {len(summary)}文字")
    else:
        summary = "[dry-run] 要約はスキップされました"
        print("  [dry-run] 要約生成をスキップ")
    
    # 5. Markdownに保存
    if not dry_run:
        summary_path = save_summary_markdown(video_id, video_info, summary, summaries_dir, summarizer.model_name)
        print(f"  要約保存: {summary_path}")
    else:
        print("  [dry-run] 要約保存をスキップ")
    
    # 6. 状態更新
    if not dry_run:
        update_state(state_path, video_id, video_info)
        print("  状態更新完了")
    else:
        print("  [dry-run] 状態更新をスキップ")
    
    return {
        'video_id': video_id,
        'title': video_info['title'],
        'summary_path': summary_path if not dry_run else None,
    }


def main():
    parser = argparse.ArgumentParser(description="単一の動画を処理 (Gemini API版)")
    parser.add_argument("video_id", help="YouTube動画IDまたはURL")
    parser.add_argument("--model", default="gemini-2.5-flash-lite", help="使用するモデル")
    parser.add_argument("--provider", default="gemini", choices=["gemini", "openrouter"], help="使用するAIプロバイダー")
    parser.add_argument("--dry-run", action="store_true", help="実際に保存せずテスト実行")
    parser.add_argument("--prompt-template", default="blog_article", 
                        choices=["strategist", "supereditor", "blog_article"],
                        help="プロンプトテンプレート")
    
    args = parser.parse_args()
    
    # パス設定
    transcripts_dir = project_root / "data" / "transcripts"
    summaries_dir = project_root / "data" / "summaries"
    state_path = project_root / "data" / "state.json"
    
    # APIキー読み込み
    api_keys = load_api_keys()
    youtube_api_key = api_keys.get("youtube_api_key")
    
    if not youtube_api_key:
        print("エラー: YouTube API キーが設定されていません")
        return 1
    
    # YouTube API クライアント
    youtube = build('youtube', 'v3', developerKey=youtube_api_key)
    
    # Summarizer 初期化
    if args.provider == "gemini":
        google_ai_api_key = api_keys.get("google_ai_api_key")
        if not google_ai_api_key:
            print("エラー: Google AI API キーが設定されていません")
            return 1
        summarizer = GeminiSummarizer(
            api_key=google_ai_api_key,
            model_name=args.model,
            prompt_template=args.prompt_template,
        )
    else:
        openrouter_api_key = api_keys.get("openrouter_api_key")
        if not openrouter_api_key:
            from openrouter_summarizer import load_api_key as load_or_key
            openrouter_api_key = load_or_key()
            
        if not openrouter_api_key:
            print("エラー: OpenRouter API キーが設定されていません")
            return 1
            
        model_name = args.model
        if model_name == "gemini-2.5-flash-lite":
            model_name = "google/gemini-2.0-flash-lite:free"
            
        summarizer = OpenRouterSummarizer(
            api_key=openrouter_api_key,
            model_name=model_name,
            prompt_template=args.prompt_template,
        )
    
    print(f"プロバイダー: {args.provider}")
    print(f"モデル: {summarizer.model_name}")
    print(f"テンプレート: {args.prompt_template}\n")
    
    try:
        # video_id抽出（URLの場合）
        video_id = args.video_id
        if 'youtube.com' in video_id or 'youtu.be' in video_id:
            import re
            patterns = [
                r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
                r'youtube\.com/watch\?.*v=([^&\n?#]+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, video_id)
                if match:
                    video_id = match.group(1)
                    break
        
        result = process_video(
            video_id,
            youtube,
            summarizer,
            transcripts_dir,
            summaries_dir,
            state_path,
            dry_run=args.dry_run,
        )
        
        print("\n✅ 処理完了!")
        print(f"  動画: {result['title']}")
        if result['summary_path']:
            print(f"  要約: {result['summary_path']}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
