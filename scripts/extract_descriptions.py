#!/usr/bin/env python3
"""
既存のJSONファイルから概要欄を抽出してテキストファイルとして保存するスクリプト

使用方法:
    uv run python scripts/extract_descriptions.py
"""

import json
import sys
from pathlib import Path

# プロジェクトルート
project_root = Path(__file__).parent.parent
transcripts_dir = project_root / "data" / "transcripts"

def extract_description(json_path: Path) -> str:
    """JSONファイルから概要欄を抽出"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('description', '')

def main():
    if not transcripts_dir.exists():
        print(f"エラー: ディレクトリが見つかりません: {transcripts_dir}")
        return 1
    
    json_files = list(transcripts_dir.glob("*.json"))
    print(f"JSONファイル数: {len(json_files)}")
    
    extracted_count = 0
    skipped_count = 0
    empty_count = 0
    
    for json_path in json_files:
        video_id = json_path.stem
        desc_path = transcripts_dir / f"{video_id}_description.txt"
        
        # 既存のファイルはスキップ
        if desc_path.exists():
            skipped_count += 1
            continue
        
        description = extract_description(json_path)
        
        if not description:
            print(f"  ⚠️ 概要欄が空: {video_id}")
            empty_count += 1
            continue
        
        with open(desc_path, 'w', encoding='utf-8') as f:
            f.write(description)
        
        print(f"  ✓ 抽出: {video_id} ({len(description)}文字)")
        extracted_count += 1
    
    print(f"\n=== 完了 ===")
    print(f"  抽出: {extracted_count}")
    print(f"  スキップ（既存）: {skipped_count}")
    print(f"  空の概要欄: {empty_count}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
