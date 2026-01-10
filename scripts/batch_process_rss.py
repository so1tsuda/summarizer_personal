#!/usr/bin/env python3
"""
RSS経由で新着動画を取得し、一括処理するスクリプト
- RSSフィードから新着動画を検出
- 各動画を処理（文字起こし + Gemini要約）
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
from scripts.process_video_gemini import (
    load_api_keys, get_video_info, get_transcript, process_video,
    GeminiSummarizer
)
from googleapiclient.discovery import build


def filter_by_duration(
    youtube,
    videos: List[Dict],
    min_duration_seconds: int = 600
) -> List[Dict]:
    """
    動画の長さでフィルタリング
    
    Args:
        youtube: YouTube API client
        videos: 動画リスト
        min_duration_seconds: 最小動画長（秒）
    
    Returns:
        フィルタリング後の動画リスト
    """
    filtered = []
    
    for video in videos:
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
                    filtered.append(video)
                    print(f"  ✓ {video['title']} ({total_seconds // 60}分)")
                else:
                    print(f"  ✗ スキップ (短い): {video['title']} ({total_seconds // 60}分)")
        except Exception as e:
            print(f"  ✗ エラー: {video['title']}: {e}")
    
    return filtered


def git_commit_and_push(message: str) -> bool:
    """
    Gitにコミット&プッシュ
    
    Args:
        message: コミットメッセージ
    
    Returns:
        成功したかどうか
    """
    try:
        # git add
        subprocess.run(['git', 'add', 'data/summaries/', 'data/transcripts/', 'data/state.json'], 
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
    
    parser = argparse.ArgumentParser(description="RSS経由で新着動画を一括処理")
    parser.add_argument("--days", type=int, default=7, help="何日前までの動画を取得するか")
    parser.add_argument("--min-duration", type=int, default=10, help="最小動画長（分）")
    parser.add_argument("--model", default="gemini-2.0-flash-exp", help="使用するGeminiモデル")
    parser.add_argument("--prompt-template", default="blog_article", help="プロンプトテンプレート")
    parser.add_argument("--auto-commit", action="store_true", help="処理後に自動的にGit commit & push")
    parser.add_argument("--dry-run", action="store_true", help="実際に保存せずテスト実行")
    parser.add_argument("--max-videos", type=int, default=5, help="一度に処理する最大動画数")
    
    args = parser.parse_args()
    
    # パス設定
    config_path = project_root / "config" / "channels.csv"
    state_path = project_root / "data" / "state.json"
    transcripts_dir = project_root / "data" / "transcripts"
    summaries_dir = project_root / "data" / "summaries"
    
    # APIキー読み込み
    api_keys = load_api_keys()
    youtube_api_key = api_keys.get("youtube_api_key")
    google_ai_api_key = api_keys.get("google_ai_api_key")
    
    if not youtube_api_key:
        print("エラー: YouTube API キーが設定されていません")
        return 1
    
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
    
    # チャンネル & 状態読み込み
    channels = load_channels_from_csv(config_path)
    state = load_state(state_path)
    
    if not channels:
        print("警告: 登録されているチャンネルがありません")
        return 0
    
    print(f"=== RSS経由 一括処理 ===")
    print(f"チャンネル数: {len(channels)}")
    print(f"モデル: {args.model}")
    print(f"テンプレート: {args.prompt_template}\n")
    
    # 1. RSSから新着動画を取得
    print("📡 RSSフィードから新着動画を取得中...")
    new_videos = fetch_all_rss_videos(channels, state, days_back=args.days)
    print(f"\n未処理の動画: {len(new_videos)}件\n")
    
    if not new_videos:
        print("新着動画はありません")
        return 0
    
    # 2. 動画の長さでフィルタリング
    print(f"⏱️  動画の長さでフィルタリング中 ({args.min_duration}分以上)...")
    filtered_videos = filter_by_duration(youtube, new_videos, min_duration_seconds=args.min_duration * 60)
    print(f"\n処理対象: {len(filtered_videos)}件\n")
    
    if not filtered_videos:
        print("処理対象の動画はありません")
        return 0
    
    # 最大数で制限
    if len(filtered_videos) > args.max_videos:
        print(f"⚠️  {args.max_videos}件に制限します")
        filtered_videos = filtered_videos[:args.max_videos]
    
    # 3. 各動画を処理
    processed_count = 0
    failed_count = 0
    
    for i, video in enumerate(filtered_videos, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(filtered_videos)}] {video['title']}")
        print(f"{'='*60}")
        
        try:
            process_video(
                video['video_id'],
                youtube,
                summarizer,
                transcripts_dir,
                summaries_dir,
                state_path,
                dry_run=args.dry_run
            )
            processed_count += 1
            
            # レート制限対策（10 RPM = 6秒間隔）
            if i < len(filtered_videos):
                print("\n⏳ レート制限対策のため6秒待機...")
                time.sleep(6)
        
        except Exception as e:
            print(f"❌ 処理失敗: {e}")
            failed_count += 1
            continue
    
    # 4. 結果サマリー
    print(f"\n{'='*60}")
    print(f"✅ 処理完了: {processed_count}件")
    print(f"❌ 失敗: {failed_count}件")
    print(f"{'='*60}\n")
    
    # 5. Git自動コミット
    if args.auto_commit and processed_count > 0 and not args.dry_run:
        print("📤 Gitにコミット&プッシュ中...")
        commit_message = f"auto: add {processed_count} new article(s) via RSS"
        git_commit_and_push(commit_message)
    
    return 0


if __name__ == "__main__":
    exit(main())
