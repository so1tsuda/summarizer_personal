#!/usr/bin/env python3
"""
チャンネルから新着動画を取得するスクリプト
- channels.csv からチャンネルリストを読み込み
- YouTube Data API で各チャンネルの動画を取得
- 10分以上の動画のみフィルタリング
- 未処理の動画IDを返す
"""

import os
import re
import csv
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def load_api_keys() -> Dict:
    """api_keys.json からAPIキーを読み込む"""
    script_dir = Path(__file__).parent.parent
    api_keys_path = script_dir / "api_keys.json"
    
    if api_keys_path.exists():
        with open(api_keys_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 環境変数からも読み込み
    return {
        "youtube_api_key": os.getenv("YOUTUBE_API_KEY", ""),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
    }


def load_channels(config_path: Path) -> List[Dict]:
    """channels.csv からチャンネルリストを読み込む"""
    channels = []
    
    if not config_path.exists():
        print(f"警告: チャンネルファイルが見つかりません: {config_path}")
        return channels
    
    with open(config_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # コメント行をスキップ
            if row.get('channel_id', '').startswith('#'):
                continue
            if row.get('channel_id'):
                channels.append({
                    'channel_id': row['channel_id'].strip(),
                    'channel_name': row.get('channel_name', '').strip(),
                    'notes': row.get('notes', '').strip(),
                })
    
    return channels


def load_state(state_path: Path) -> Dict:
    """state.json から処理済み動画リストを読み込む"""
    if state_path.exists():
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"processed_videos": {}}


def save_state(state_path: Path, state: Dict):
    """state.json に処理済み動画リストを保存"""
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def parse_duration(duration: str) -> int:
    """ISO 8601 duration を秒数に変換 (例: PT15M30S -> 930)"""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds


def get_channel_videos(
    youtube,
    channel_id: str,
    max_results: int = 20,
    published_after: Optional[datetime] = None
) -> List[Dict]:
    """チャンネルの動画リストを取得"""
    videos = []
    
    try:
        # チャンネルのアップロードプレイリストIDを取得
        channel_response = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        ).execute()
        
        if not channel_response.get('items'):
            print(f"  チャンネルが見つかりません: {channel_id}")
            return videos
        
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # プレイリストから動画を取得
        playlist_response = youtube.playlistItems().list(
            part='snippet,contentDetails',
            playlistId=uploads_playlist_id,
            maxResults=max_results
        ).execute()
        
        video_ids = [item['contentDetails']['videoId'] for item in playlist_response.get('items', [])]
        
        if not video_ids:
            return videos
        
        # 動画の詳細情報（duration含む）を取得
        videos_response = youtube.videos().list(
            part='snippet,contentDetails',
            id=','.join(video_ids)
        ).execute()
        
        for video in videos_response.get('items', []):
            published_at = datetime.fromisoformat(
                video['snippet']['publishedAt'].replace('Z', '+00:00')
            )
            
            # 公開日フィルタ
            if published_after and published_at < published_after:
                continue
            
            videos.append({
                'video_id': video['id'],
                'title': video['snippet']['title'],
                'channel_id': video['snippet']['channelId'],
                'channel_title': video['snippet']['channelTitle'],
                'published_at': video['snippet']['publishedAt'],
                'duration': video['contentDetails']['duration'],
                'duration_seconds': parse_duration(video['contentDetails']['duration']),
                'thumbnail': video['snippet']['thumbnails'].get('high', {}).get('url', ''),
            })
        
    except HttpError as e:
        print(f"  YouTube APIエラー: {e}")
    
    return videos


def fetch_new_videos(
    youtube,
    channels: List[Dict],
    state: Dict,
    min_duration_seconds: int = 600,  # 10分
    days_back: int = 30
) -> List[Dict]:
    """
    すべてのチャンネルから新着動画を取得
    
    Returns:
        未処理かつ10分以上の動画のリスト
    """
    new_videos = []
    processed_ids = set(state.get('processed_videos', {}).keys())
    published_after = datetime.now().astimezone() - timedelta(days=days_back)
    
    for channel in channels:
        channel_id = channel['channel_id']
        channel_name = channel.get('channel_name', channel_id)
        print(f"チャンネルをチェック中: {channel_name}")
        
        videos = get_channel_videos(youtube, channel_id, published_after=published_after)
        
        for video in videos:
            # 処理済みチェック
            if video['video_id'] in processed_ids:
                continue
            
            # 10分以上チェック
            if video['duration_seconds'] < min_duration_seconds:
                continue
            
            new_videos.append(video)
            print(f"  ✓ 新着: {video['title']} ({video['duration_seconds'] // 60}分)")
    
    return new_videos


def main():
    parser = argparse.ArgumentParser(description="チャンネルから新着動画を取得")
    parser.add_argument("--days", type=int, default=30, help="何日前までの動画を取得するか")
    parser.add_argument("--min-duration", type=int, default=10, help="最小動画長（分）")
    parser.add_argument("--dry-run", action="store_true", help="取得のみで処理しない")
    parser.add_argument("-o", "--output", help="出力JSONファイル")
    
    args = parser.parse_args()
    
    # パス設定
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config" / "channels.csv"
    state_path = project_root / "data" / "state.json"
    
    # APIキー読み込み
    api_keys = load_api_keys()
    youtube_api_key = api_keys.get("youtube_api_key")
    
    if not youtube_api_key:
        print("エラー: YouTube API キーが設定されていません")
        print("api_keys.json に youtube_api_key を設定してください")
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
    
    print(f"登録チャンネル数: {len(channels)}")
    print(f"過去{args.days}日間の動画を取得します（{args.min_duration}分以上）\n")
    
    # 新着動画を取得
    new_videos = fetch_new_videos(
        youtube,
        channels,
        state,
        min_duration_seconds=args.min_duration * 60,
        days_back=args.days
    )
    
    print(f"\n未処理の動画: {len(new_videos)}件")
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(new_videos, f, ensure_ascii=False, indent=2)
        print(f"結果を保存しました: {args.output}")
    else:
        for video in new_videos:
            print(f"  - {video['video_id']}: {video['title']}")
    
    return 0


if __name__ == "__main__":
    exit(main())
