#!/usr/bin/env python3
"""
要約Markdownファイルのフロントマターを修復するスクリプト
- JSONファイルからメタデータを取得してフロントマターを再構築
- JSONにタイトル等がない場合は概要欄ファイルから抽出を試みる
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime

# パス設定
PROJECT_ROOT = Path(__file__).parent.parent
TRANSCRIPT_DIR = PROJECT_ROOT / "data" / "transcripts"
SUMMARY_DIR = PROJECT_ROOT / "data" / "summaries"

def extract_metadata_from_description(desc_path: Path):
    """概要欄テキストからメタデータを抽出する（簡易実装）"""
    if not desc_path.exists():
        return None, None
    
    content = desc_path.read_text(encoding='utf-8')
    
    # 簡易的な抽出ロジック（実際の内容に合わせて要調整）
    # PIVOTなどの形式を想定
    title = None
    channel = None
    
    # タイトルの抽出（1行目にあることが多い、または特定のキーワードの周辺）
    lines = content.splitlines()
    if lines:
        title = lines[0].strip()
        if len(title) < 5: # 短すぎる場合はタイトルっぽくない
            title = None

    return title, channel

def repair_file(md_path: Path):
    video_id = md_path.stem
    json_path = TRANSCRIPT_DIR / f"{video_id}.json"
    desc_path = TRANSCRIPT_DIR / f"{video_id}_description.txt"
    
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # すでにフロントマターがあるかチェック
    if content.startswith('---'):
        # すでにフロントマターがある場合でも、内容をチェック
        if 'title: "Untitled"' in content or 'channel: "Unknown"' in content:
            print(f"  [Fixing] {video_id}: Frontmatter exists but has placeholders.")
            # 続きの処理へ
        else:
            return False

    print(f"Repairing {video_id}...")
    
    metadata = {}
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    
    title = metadata.get('title')
    channel = metadata.get('channel')
    published_at = metadata.get('published_at', '')[:10]
    
    # メタデータが不足している場合のフォールバック
    if not title or title == "Untitled" or not channel or channel == "Unknown":
        d_title, d_channel = extract_metadata_from_description(desc_path)
        if not title or title == "Untitled":
            title = d_title or "Untitled"
        if not channel or channel == "Unknown":
            channel = d_channel or "Unknown"

    # 特殊なケース：タイトルに改行が含まれる場合
    if title:
        title = title.replace('\n', ' ').replace('"', '\\"')

    frontmatter = f"""---
title: "{title}"
video_id: "{video_id}"
channel: "{channel}"
published_at: "{published_at}"
youtube_url: "https://www.youtube.com/watch?v={video_id}"
thumbnail: "https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
summarized_at: "{datetime.now().isoformat()}"
model: "repaired"
---

"""
    
    # 既存のフロントマターを削除（もしあれば）
    if content.startswith('---'):
        # 2つ目の --- を探す
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    
    new_content = frontmatter + content.strip()
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def main():
    md_files = list(SUMMARY_DIR.glob("*.md"))
    repaired_count = 0
    
    for md_path in md_files:
        if repair_file(md_path):
            repaired_count += 1
            print(f"  ✓ Repaired: {md_path.name}")
            
    print(f"\nFinished. Repaired {repaired_count} files.")

if __name__ == "__main__":
    main()
