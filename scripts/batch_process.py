#!/usr/bin/env python3
"""
バッチ処理スクリプト
- fetch_new_videos.py で新着動画を取得
- 各動画を process_video.py で処理
- エラーハンドリングとリトライ
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.fetch_new_videos import (
    load_api_keys,
    load_channels,
    load_state,
    fetch_new_videos,
)
from scripts.process_video import process_video
from youtube_transcript_tool import YouTubeTranscriptToolOpenRouter

from googleapiclient.discovery import build


def main():
    parser = argparse.ArgumentParser(description="新着動画をバッチ処理")
    parser.add_argument("--days", type=int, default=7, help="何日前までの動画を処理するか")
    parser.add_argument("--min-duration", type=int, default=10, help="最小動画長（分）")
    parser.add_argument("--limit", type=int, default=5, help="処理する動画の最大数")
    parser.add_argument("--model", default="google/gemini-2.0-flash-001", help="使用するモデル")
    parser.add_argument("--dry-run", action="store_true", help="実際に処理せずテスト実行")
    parser.add_argument("--delay", type=int, default=5, help="動画間の待機時間（秒）")
    
    args = parser.parse_args()
    
    # パス設定
    config_path = project_root / "config" / "channels.csv"
    state_path = project_root / "data" / "state.json"
    transcripts_dir = project_root / "data" / "transcripts"
    summaries_dir = project_root / "data" / "summaries"
    
    # APIキー読み込み
    api_keys = load_api_keys()
    youtube_api_key = api_keys.get("youtube_api_key")
    openrouter_api_key = api_keys.get("openrouter_api_key")
    
    if not youtube_api_key:
        print("エラー: YouTube API キーが設定されていません")
        return 1
    
    if not openrouter_api_key:
        print("エラー: OpenRouter API キーが設定されていません")
        return 1
    
    # YouTube API クライアント
    youtube = build('youtube', 'v3', developerKey=youtube_api_key)
    
    # データ読み込み
    channels = load_channels(config_path)
    state = load_state(state_path)
    
    if not channels:
        print("警告: 登録されているチャンネルがありません")
        print(f"  {config_path} にチャンネルを追加してください")
        return 0
    
    print(f"=== バッチ処理開始 ===")
    print(f"登録チャンネル数: {len(channels)}")
    print(f"対象期間: 過去{args.days}日間")
    print(f"最小動画長: {args.min_duration}分")
    print(f"処理上限: {args.limit}件")
    print(f"モデル: {args.model}")
    print()
    
    # 新着動画を取得
    print("--- 新着動画を取得中 ---")
    new_videos = fetch_new_videos(
        youtube,
        channels,
        state,
        min_duration_seconds=args.min_duration * 60,
        days_back=args.days,
    )
    
    if not new_videos:
        print("\n処理対象の動画はありません")
        return 0
    
    # 処理上限を適用
    videos_to_process = new_videos[:args.limit]
    print(f"\n処理対象: {len(videos_to_process)}件 (全{len(new_videos)}件中)")
    
    if args.dry_run:
        print("\n[dry-run] 以下の動画が処理対象です:")
        for video in videos_to_process:
            print(f"  - {video['video_id']}: {video['title']}")
        return 0
    
    # ツール初期化
    tool = YouTubeTranscriptToolOpenRouter(
        youtube_api_key=youtube_api_key,
        openrouter_api_key=openrouter_api_key,
        model=args.model,
        output_dir=str(project_root),
        prompt_template="supereditor",
    )
    
    # 各動画を処理
    print("\n--- 動画を処理中 ---")
    results: List[Dict] = []
    errors: List[Dict] = []
    
    for i, video in enumerate(videos_to_process, 1):
        video_id = video['video_id']
        print(f"\n[{i}/{len(videos_to_process)}] {video['title']}")
        
        try:
            result = process_video(
                video_id,
                tool,
                transcripts_dir,
                summaries_dir,
                state_path,
                dry_run=False,
            )
            results.append(result)
            print(f"  ✅ 完了")
            
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            errors.append({
                "video_id": video_id,
                "title": video['title'],
                "error": str(e),
            })
        
        # 次の動画まで待機（APIレート制限対策）
        if i < len(videos_to_process):
            print(f"  {args.delay}秒待機中...")
            time.sleep(args.delay)
    
    # 結果サマリー
    print("\n=== 処理完了 ===")
    print(f"成功: {len(results)}件")
    print(f"失敗: {len(errors)}件")
    
    if errors:
        print("\n失敗した動画:")
        for err in errors:
            print(f"  - {err['video_id']}: {err['error']}")
    
    return 0 if not errors else 1


if __name__ == "__main__":
    exit(main())
