#!/usr/bin/env python3
"""
RSS経由で新着動画を取得し、バックログキューから処理するスクリプト
- RSSフィードから新着動画を検出 → backlog.jsonに追加
- キューから1本取り出して処理（Gemini要約）
- オプションでGitに自動コミット&プッシュ
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import List, Dict

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.rss_fetch import load_channels_from_csv, load_state, fetch_all_rss_videos
from scripts.process_video import (
    load_api_keys, get_video_info, get_transcript, process_video,
    GeminiSummarizer
)
from googleapiclient.discovery import build


def load_backlog(backlog_path: Path) -> Dict:
    """backlog.json を読み込む"""
    if backlog_path.exists():
        import json
        with open(backlog_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "queue": [],
        "failed": [],
        "last_processed_at": None
    }


def save_backlog(backlog_path: Path, backlog: Dict):
    """backlog.json に保存"""
    import json
    with open(backlog_path, 'w', encoding='utf-8') as f:
        json.dump(backlog, f, ensure_ascii=False, indent=2)


def add_to_backlog(backlog: Dict, videos: List[Dict], state: Dict) -> int:
    """
    新着動画をバックログに追加
    
    Returns:
        追加された動画数
    """
    added_count = 0
    processed_ids = set(state.get('processed_videos', {}).keys())
    
    for video in videos:
        video_id = video['video_id']
        
        # 処理済みチェック
        if video_id in processed_ids:
            continue
        
        # キューに既に存在するかチェック
        if any(v['video_id'] == video_id for v in backlog['queue']):
            continue
        
        # failedに存在するかチェック
        if any(v['video_id'] == video_id for v in backlog['failed']):
            continue
        
        from datetime import datetime
        backlog['queue'].append({
            'video_id': video_id,
            'title': video.get('title', ''),
            'channel': video.get('channel_title', ''),
            'published_at': video.get('published_at', ''),
            'lang': video.get('lang', 'ja'),
            'added_at': datetime.now().isoformat()
        })
        added_count += 1
    
    return added_count


def filter_by_duration(
    youtube,
    video: Dict,
    min_duration_seconds: int = 600
) -> bool:
    """
    動画の長さでフィルタリング
    
    Returns:
        条件を満たす場合True
    """
    try:
        video_info = get_video_info(youtube, video['video_id'])
        
        # duration をパース (PT15M30S -> 930秒)
        import re
        duration = video_info.get('duration', '')
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            if total_seconds >= min_duration_seconds:
                video['duration_seconds'] = total_seconds
                video['duration'] = duration
                video['thumbnail'] = video_info.get('thumbnail', '')
                video['description'] = video_info.get('description', '')
                return True
    except Exception as e:
        print(f"  ✗ エラー: {video.get('title', video['video_id'])}: {e}")
    
    return False


def get_channel_lang(channels: List[Dict], channel_name: str) -> str:
    """
    チャンネル名から言語設定を取得
    
    Args:
        channels: チャンネルリスト
        channel_name: チャンネル名
    
    Returns:
        言語コード ('ja' または 'en'、見つからない場合は 'ja')
    """
    for channel in channels:
        if channel.get('channel_name', '').strip() == channel_name.strip():
            return channel.get('lang', 'ja')
    return 'ja'  # デフォルトは日本語


def git_commit_and_push(message: str) -> bool:
    """
    Gitにコミット&プッシュ
    
    Returns:
        成功したかどうか
    """
    try:
        # git add
        subprocess.run(['git', 'add', 'data/transcripts/', 'data/summaries/', 'data/state.json', 'data/backlog.json'],
                      cwd=project_root, check=True)
        
        # git commit
        result = subprocess.run(['git', 'commit', '-m', message], 
                               cwd=project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            if 'nothing to commit' in result.stdout:
                print("  変更なし、コミットをスキップ")
                return False
            else:
                print(f"  コミット失敗: {result.stderr}")
                return False
        
        # git push
        subprocess.run(['git', 'push', 'origin', 'master'], 
                      cwd=project_root, check=True)
        
        print("  ✓ Git push 完了")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Git操作失敗: {e}")
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="RSS経由で新着動画を取得し、バックログから処理")
    parser.add_argument("--days", type=int, default=7, help="何日前までの動画を取得するか")
    parser.add_argument("--min-duration", type=int, default=10, help="最小動画長（分）")
    parser.add_argument("--model", default="gemini-2.5-flash", help="使用するGeminiモデル")
    parser.add_argument("--provider", default="gemini", choices=["gemini", "kilocode"], help="使用するAIプロバイダー (kilocodeは文字起こし保存のみ)")
    parser.add_argument("--prompt-template", default="blog_article", help="プロンプトテンプレート")
    parser.add_argument("--auto-commit", action="store_true", help="処理後に自動的にGit commit & push")
    parser.add_argument("--dry-run", action="store_true", help="実際に保存せずテスト実行")
    parser.add_argument("--process-count", type=int, default=1, help="一度に処理する動画数")
    
    args = parser.parse_args()
    
    # パス設定
    config_path = project_root / "config" / "channels.csv"
    state_path = project_root / "data" / "state.json"
    backlog_path = project_root / "data" / "backlog.json"
    transcripts_dir = project_root / "data" / "transcripts"
    summaries_dir = project_root / "data" / "summaries"
    
    # APIキー読み込み
    api_keys = load_api_keys()
    youtube_api_key = api_keys.get("youtube_api_key")
    
    if not youtube_api_key:
        print("エラー: YouTube API キーが設定されていません")
        return 1

    # Summarizer 初期化 (kilocode モードではスキップ)
    summarizer = None
    skip_summarization = False
    
    if args.provider == "kilocode":
        skip_summarization = True
        print(f"プロバイダー: {args.provider}")
        print("モード: 文字起こし・概要欄保存のみ（LLM要約はKilo Code CLIで別途処理）\n")
    else:
        google_ai_api_key = api_keys.get("google_ai_api_key")
        if not google_ai_api_key:
            print("エラー: Google AI API キーが設定されていません")
            return 1
            
        # クライアント初期化
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        summarizer = GeminiSummarizer(
            api_key=google_ai_api_key,
            model_name=args.model,
            prompt_template=args.prompt_template,
        )
    
    # YouTubeクライアントは常に必要
    youtube = build('youtube', 'v3', developerKey=youtube_api_key)
    
    # データ読み込み
    channels = load_channels_from_csv(config_path)
    state = load_state(state_path)
    backlog = load_backlog(backlog_path)
    
    if not channels:
        print("警告: 登録されているチャンネルがありません")
        return 0
    
    print(f"=== RSS経由 バックログ処理 ===")
    print(f"チャンネル数: {len(channels)}")
    print(f"モデル: {args.model}")
    print(f"テンプレート: {args.prompt_template}\n")
    
    # 1. RSSから新着動画を取得してバックログに追加
    print("📡 RSSフィードから新着動画を取得中...")
    new_videos = fetch_all_rss_videos(channels, state, days_back=args.days)
    print(f"  未処理の動画: {len(new_videos)}件")
    
    if new_videos:
        added_count = add_to_backlog(backlog, new_videos, state)
        print(f"  ✓ バックログに追加: {added_count}件")
        if not args.dry_run:
            save_backlog(backlog_path, backlog)
    
    # 2. バックログから処理
    queue = backlog.get('queue', [])
    print(f"\n📋 現在のバックログ: {len(queue)}件")
    
    if not queue:
        print("処理対象の動画はありません")
        return 0
    
    # 目標とする処理数
    target_count = args.process_count
    print(f"  目標処理数: {target_count}件\n")
    
    processed_count = 0
    failed_count = 0
    skipped_count = 0
    
    # 目標数に達するか、キューが空になるまでループ
    while processed_count < target_count and queue:
        video = queue[0]  # 常に先頭から取得
        
        print(f"\n{'='*60}")
        print(f"[{processed_count+1}/{target_count}] {video['title']}")
        print(f"{'='*60}")
        
        # 動画の長さチェック
        if not filter_by_duration(youtube, video, min_duration_seconds=args.min_duration * 60):
            print(f"  ✗ スキップ (短い動画) → 次の動画を探します")
            queue.pop(0)
            skipped_count += 1
            continue
        
        try:
            # チャンネルの言語設定を取得
            # バックログに lang がない場合は channels.csv から取得（後方互換性）
            video_lang = video.get('lang')
            if not video_lang:
                video_lang = get_channel_lang(channels, video.get('channel', ''))
            print(f"  字幕優先言語: {video_lang}")
            
            process_video(
                video['video_id'],
                youtube,
                summarizer,
                transcripts_dir,
                summaries_dir,
                state_path,
                dry_run=args.dry_run,
                skip_summarization=skip_summarization
            )
            
            # 成功したらキューから削除
            queue.pop(0)
            processed_count += 1
            
            # 状態を再読み込み（process_videoで更新されるため）
            state = load_state(state_path)
            
            # レート制限対策（10 RPM = 6秒間隔）
            if processed_count < target_count and queue:
                import random
                delay = random.randint(5, 30)
                print(f"\n⏳ IPバン対策のため {delay}秒待機...")
                time.sleep(delay)
        
        except Exception as e:
            print(f"❌ 処理失敗: {e}")
            
            # 失敗したらfailedリストに移動
            failed_video = queue.pop(0)
            backlog['failed'].append(failed_video)
            failed_count += 1
            continue
    
    if skipped_count > 0:
        print(f"\n📌 スキップした短い動画: {skipped_count}件")
    
    # バックログ保存
    if not args.dry_run:
        from datetime import datetime
        backlog['last_processed_at'] = datetime.now().isoformat()
        save_backlog(backlog_path, backlog)
    
    # 3. 結果サマリー
    print(f"\n{'='*60}")
    print(f"✅ 処理完了: {processed_count}件")
    print(f"❌ 失敗: {failed_count}件")
    print(f"📋 残りのバックログ: {len(queue)}件")
    print(f"{'='*60}\n")
    
    # 4. Git自動コミット
    if args.auto_commit and processed_count > 0 and not args.dry_run:
        print("📤 Gitにコミット&プッシュ中...")
        commit_message = f"auto: process {processed_count} video(s) from backlog"
        git_commit_and_push(commit_message)
    
    return 0


if __name__ == "__main__":
    exit(main())
