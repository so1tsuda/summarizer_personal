#!/usr/bin/env python3
"""
バックログ管理ツール
- 処理待ち動画キューの管理
- 過去動画のインポート
- キュー一覧表示
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.rss_fetch import fetch_rss_videos, load_channels_from_csv
from googleapiclient.discovery import build


def load_backlog(backlog_path: Path) -> Dict:
    """backlog.json を読み込む"""
    if backlog_path.exists():
        with open(backlog_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "queue": [],
        "failed": [],
        "last_processed_at": None
    }


def save_backlog(backlog_path: Path, backlog: Dict):
    """backlog.json に保存"""
    with open(backlog_path, 'w', encoding='utf-8') as f:
        json.dump(backlog, f, ensure_ascii=False, indent=2)


def load_state(state_path: Path) -> Dict:
    """state.json から処理済み動画リストを読み込む"""
    if state_path.exists():
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"processed_videos": {}}


def add_to_queue(backlog: Dict, video: Dict, state: Dict) -> bool:
    """
    キューに動画を追加（重複チェック付き）
    
    Returns:
        追加された場合True
    """
    video_id = video['video_id']
    
    # 処理済みチェック
    if video_id in state.get('processed_videos', {}):
        return False
    
    # キューに既に存在するかチェック
    if any(v['video_id'] == video_id for v in backlog['queue']):
        return False
    
    # failedに存在するかチェック
    if any(v['video_id'] == video_id for v in backlog['failed']):
        return False
    
    backlog['queue'].append({
        'video_id': video_id,
        'title': video.get('title', ''),
        'channel': video.get('channel_title', ''),
        'published_at': video.get('published_at', ''),
        'added_at': datetime.now().isoformat()
    })
    
    return True


def import_channel_videos(
    youtube,
    channel_id: str,
    channel_name: str,
    days_back: int,
    backlog: Dict,
    state: Dict
) -> int:
    """
    チャンネルの過去動画をインポート
    
    Returns:
        追加された動画数
    """
    print(f"チャンネルから過去動画をインポート中: {channel_name}")
    print(f"  期間: 過去{days_back}日")
    
    # RSSから取得
    videos = fetch_rss_videos(channel_id, channel_name, days_back)
    
    added_count = 0
    for video in videos:
        if add_to_queue(backlog, video, state):
            added_count += 1
            print(f"  ✓ 追加: {video['title']}")
    
    return added_count


def list_queue(backlog: Dict):
    """キュー一覧を表示"""
    queue = backlog.get('queue', [])
    failed = backlog.get('failed', [])
    
    print(f"\n=== 処理待ちキュー ({len(queue)}件) ===")
    if queue:
        for i, video in enumerate(queue[:10], 1):
            print(f"{i}. [{video['video_id']}] {video['title']}")
            print(f"   チャンネル: {video['channel']}")
        
        if len(queue) > 10:
            print(f"... 他 {len(queue) - 10}件")
    else:
        print("  (空)")
    
    print(f"\n=== 失敗リスト ({len(failed)}件) ===")
    if failed:
        for i, video in enumerate(failed[:5], 1):
            print(f"{i}. [{video['video_id']}] {video['title']}")
        
        if len(failed) > 5:
            print(f"... 他 {len(failed) - 5}件")
    else:
        print("  (空)")


def retry_failed(backlog: Dict) -> int:
    """失敗リストをキューに戻す"""
    failed = backlog.get('failed', [])
    count = len(failed)
    
    if count > 0:
        backlog['queue'].extend(failed)
        backlog['failed'] = []
        print(f"✓ {count}件の失敗動画をキューに戻しました")
    else:
        print("失敗リストは空です")
    
    return count


def main():
    parser = argparse.ArgumentParser(description="バックログ管理ツール")
    parser.add_argument("--list", action="store_true", help="キュー一覧を表示")
    parser.add_argument("--add", metavar="VIDEO_ID", help="動画を手動で追加")
    parser.add_argument("--import-channel", metavar="CHANNEL_ID", help="チャンネルの過去動画をインポート")
    parser.add_argument("--days", type=int, default=30, help="インポート期間（日）")
    parser.add_argument("--retry-failed", action="store_true", help="失敗リストをキューに戻す")
    
    args = parser.parse_args()
    
    # パス設定
    backlog_path = project_root / "data" / "backlog.json"
    state_path = project_root / "data" / "state.json"
    config_path = project_root / "config" / "channels.csv"
    
    # データ読み込み
    backlog = load_backlog(backlog_path)
    state = load_state(state_path)
    
    # コマンド実行
    if args.list:
        list_queue(backlog)
        return 0
    
    elif args.retry_failed:
        retry_failed(backlog)
        save_backlog(backlog_path, backlog)
        return 0
    
    elif args.add:
        # YouTube APIで動画情報を取得
        try:
            from dotenv import load_dotenv
            env_path = project_root / ".env"
            if env_path.exists():
                load_dotenv(env_path)
        except ImportError:
            pass
        
        youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        if not youtube_api_key:
            print("エラー: YouTube API キーが設定されていません")
            return 1
        
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        
        try:
            response = youtube.videos().list(
                part='snippet',
                id=args.add
            ).execute()
            
            if not response.get('items'):
                print(f"エラー: 動画が見つかりません: {args.add}")
                return 1
            
            video = response['items'][0]['snippet']
            video_data = {
                'video_id': args.add,
                'title': video['title'],
                'channel_title': video['channelTitle'],
                'published_at': video['publishedAt']
            }
            
            if add_to_queue(backlog, video_data, state):
                print(f"✓ 追加: {video_data['title']}")
                save_backlog(backlog_path, backlog)
            else:
                print(f"スキップ: 既に処理済みまたはキューに存在します")
        
        except Exception as e:
            print(f"エラー: {e}")
            return 1
        
        return 0
    
    elif args.import_channel:
        # チャンネル情報を取得
        channels = load_channels_from_csv(config_path)
        channel = next((c for c in channels if c['channel_id'] == args.import_channel), None)
        
        if not channel:
            print(f"エラー: チャンネルが見つかりません: {args.import_channel}")
            print(f"  {config_path} に登録されているか確認してください")
            return 1
        
        # YouTube API初期化
        try:
            from dotenv import load_dotenv
            env_path = project_root / ".env"
            if env_path.exists():
                load_dotenv(env_path)
        except ImportError:
            pass
        
        youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        if not youtube_api_key:
            print("エラー: YouTube API キーが設定されていません")
            return 1
        
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        
        # インポート実行
        added_count = import_channel_videos(
            youtube,
            args.import_channel,
            channel['channel_name'],
            args.days,
            backlog,
            state
        )
        
        save_backlog(backlog_path, backlog)
        print(f"\n✓ {added_count}件の動画をキューに追加しました")
        print(f"  現在のキュー: {len(backlog['queue'])}件")
        
        return 0
    
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    exit(main())
