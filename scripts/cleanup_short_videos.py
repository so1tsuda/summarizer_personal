#!/usr/bin/env python3
import os
import json
import re
from pathlib import Path

project_root = Path(__file__).parent.parent
transcripts_dir = project_root / "data" / "transcripts"
summaries_dir = project_root / "data" / "summaries"
state_path = project_root / "data" / "state.json"
backlog_path = project_root / "data" / "backlog.json"

def parse_duration(duration: str) -> int:
    """ISO 8601 duration を秒数に変換"""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds

def cleanup():
    print("=== Short Video Cleanup (<= 10 min) ===")
    
    deleted_ids = []
    
    # 1. transcriptsフォルダをスキャン
    if not transcripts_dir.exists():
        print("Transcripts directory not found.")
        return

    for json_file in transcripts_dir.glob("*.json"):
        if "_defuddle" in json_file.name: continue
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            video_id = data.get("video_id")
            duration_str = data.get("duration", "")
            duration_seconds = parse_duration(duration_str)
            
            if duration_seconds <= 600:
                print(f"Deleting short video: {video_id} ({duration_str}, {data.get('title')[:30]}...)")
                
                # Associated files
                files_to_delete = [
                    json_file,
                    transcripts_dir / f"{video_id}_cleaned.txt",
                    transcripts_dir / f"{video_id}_description.txt",
                    transcripts_dir / f"{video_id}_defuddle.md",
                    summaries_dir / f"{video_id}.md"
                ]
                
                for f in files_to_delete:
                    if f.exists():
                        f.unlink()
                        print(f"  - Deleted: {f.name}")
                
                deleted_ids.append(video_id)
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")

    if not deleted_ids:
        print("No short videos found to delete.")
        return

    # 2. state.json の更新
    if state_path.exists():
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        original_count = len(state.get("processed_videos", {}))
        for vid in deleted_ids:
            if vid in state.get("processed_videos", {}):
                del state["processed_videos"][vid]
        
        new_count = len(state.get("processed_videos", {}))
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print(f"Updated state.json: {original_count} -> {new_count} entries")

    # 3. backlog.json の更新
    if backlog_path.exists():
        with open(backlog_path, 'r', encoding='utf-8') as f:
            backlog = json.load(f)
        
        # queue
        original_q = len(backlog.get("queue", []))
        backlog["queue"] = [v for v in backlog.get("queue", []) if v["video_id"] not in deleted_ids]
        new_q = len(backlog["queue"])
        
        # failed
        original_f = len(backlog.get("failed", []))
        backlog["failed"] = [v for v in backlog.get("failed", []) if v["video_id"] not in deleted_ids]
        new_f = len(backlog["failed"])
        
        with open(backlog_path, 'w', encoding='utf-8') as f:
            json.dump(backlog, f, ensure_ascii=False, indent=2)
        print(f"Updated backlog.json: Queue {original_q}->{new_q}, Failed {original_f}->{new_f}")

    print(f"\nCleanup complete. Total videos removed: {len(deleted_ids)}")

if __name__ == "__main__":
    cleanup()
