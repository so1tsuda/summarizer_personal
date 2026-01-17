#!/usr/bin/env python3
"""
RSS経由でYouTubeチャンネルの新着動画を取得するスクリプト
- YouTube RSSフィード (https://www.youtube.com/feeds/videos.xml?channel_id=...) を使用
- API quota を消費せずに新着動画をチェック
- 動画の詳細情報（duration等）は必要時のみYouTube APIで取得
"""

import os
import json
import argparse
import feedparser
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from pathlib import Path


def load_state(state_path: Path) -> Dict:
    """state.json から処理済み動画リストを読み込む"""
    if state_path.exists():
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"processed_videos": {}}


def get_channel_rss_url(channel_id: str) -> str:
    """チャンネルIDからRSS URLを生成"""
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def fetch_rss_videos(
    channel_id: str,
    channel_name: str,
    days_back: int = 7,
    lang: str = 'ja'
) -> List[Dict]:
    """
    RSSフィードから新着動画を取得
    
    Args:
        channel_id: YouTubeチャンネルID
        channel_name: チャンネル名（表示用）
        days_back: 何日前までの動画を取得するか
        lang: チャンネルの優先言語
    
    Returns:
        動画情報のリスト
    """
    rss_url = get_channel_rss_url(channel_id)
    videos = []
    
    try:
        feed = feedparser.parse(rss_url)
        
        if feed.bozo:
            print(f"  警告: RSSフィードのパースに失敗しました ({channel_name})")
            return videos
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        for entry in feed.entries:
            # published は datetime オブジェクト
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            
            if published < cutoff_date:
                continue
            
            # video_id は yt:video_id タグから取得
            video_id = entry.yt_videoid if hasattr(entry, 'yt_videoid') else entry.id.split(':')[-1]
            
            videos.append({
                'video_id': video_id,
                'title': entry.title,
                'channel_id': channel_id,
                'channel_title': channel_name,
                'published_at': published.isoformat(),
                'link': entry.link,
                'lang': lang,
            })
        
    except Exception as e:
        print(f"  エラー: RSSフィードの取得に失敗しました ({channel_name}): {e}")
    
    return videos


def fetch_all_rss_videos(
    channels: List[Dict],
    state: Dict,
    days_back: int = 7
) -> List[Dict]:
    """
    すべてのチャンネルからRSS経由で新着動画を取得
    
    Args:
        channels: チャンネル情報のリスト
        state: 処理済み動画の状態
        days_back: 何日前までの動画を取得するか
    
    Returns:
        未処理の動画リスト
    """
    new_videos = []
    processed_ids = set(state.get('processed_videos', {}).keys())
    
    for i, channel in enumerate(channels):
        channel_id = channel['channel_id']
        channel_name = channel.get('channel_name', channel_id)
        channel_lang = channel.get('lang', 'ja')
        
        # IPバン対策: チャンネルごとに 2〜5秒のランダム待機 (最初のチャンネル以外)
        if i > 0:
            import time
            import random
            delay = random.uniform(2, 5)
            print(f"  ⏳ 次のチャンネルまで待機中... ({delay:.1f}s)")
            time.sleep(delay)

        print(f"チャンネルをチェック中 (RSS): {channel_name} (言語: {channel_lang})")
        
        videos = fetch_rss_videos(channel_id, channel_name, days_back, lang=channel_lang)
        
        for video in videos:
            # 処理済みチェック
            if video['video_id'] in processed_ids:
                continue
            
            new_videos.append(video)
            print(f"  ✓ 新着: {video['title']}")
    
    return new_videos


def load_channels_from_csv(config_path: Path) -> List[Dict]:
    """channels.csv からチャンネルリストを読み込む"""
    import csv
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
                    'lang': row.get('lang', 'ja').strip(),  # デフォルトは日本語
                    'notes': row.get('notes', '').strip(),
                })
    
    return channels


def main():
    parser = argparse.ArgumentParser(description="RSS経由でチャンネルから新着動画を取得")
    parser.add_argument("--days", type=int, default=7, help="何日前までの動画を取得するか")
    parser.add_argument("-o", "--output", help="出力JSONファイル")
    
    args = parser.parse_args()
    
    # パス設定
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config" / "channels.csv"
    state_path = project_root / "data" / "state.json"
    
    # データ読み込み
    channels = load_channels_from_csv(config_path)
    state = load_state(state_path)
    
    if not channels:
        print("警告: 登録されているチャンネルがありません")
        print(f"  {config_path} にチャンネルを追加してください")
        return 0
    
    print(f"登録チャンネル数: {len(channels)}")
    print(f"過去{args.days}日間の動画を取得します (RSS)\n")
    
    # 新着動画を取得
    new_videos = fetch_all_rss_videos(channels, state, days_back=args.days)
    
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
