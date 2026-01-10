#!/usr/bin/env python3
"""
単一の動画を処理するスクリプト
- 文字起こしを取得してJSONに保存
- OpenRouter経由でGemini 2.0 Flashを使って要約
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

from youtube_transcript_tool import YouTubeTranscriptToolOpenRouter, load_api_keys


def save_transcript_json(
    video_id: str,
    video_info: Dict,
    transcript: list,
    output_dir: Path
) -> Path:
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


def save_summary_markdown(
    video_id: str,
    video_info: Dict,
    summary: str,
    output_dir: Path
) -> Path:
    """要約をMarkdownファイルに保存"""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_id}.md"
    
    # タイトルのエスケープ（f-string内ではバックスラッシュ使用不可）
    escaped_title = video_info.get('title', '').replace('"', '\\"')
    published_date = video_info.get('published_at', '')[:10]
    
    # frontmatter
    frontmatter = f"""---
title: "{escaped_title}"
video_id: "{video_id}"
channel: "{video_info.get('channel', '')}"
published_at: "{published_date}"
youtube_url: "https://www.youtube.com/watch?v={video_id}"
thumbnail: "{video_info.get('thumbnail', '')}"
summarized_at: "{datetime.now().isoformat()}"
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
    video_id_or_url: str,
    tool: YouTubeTranscriptToolOpenRouter,
    transcripts_dir: Path,
    summaries_dir: Path,
    state_path: Path,
    dry_run: bool = False
) -> Dict:
    """
    動画を処理
    
    Returns:
        処理結果の辞書
    """
    # URLからvideo_idを抽出
    video_id = tool.extract_video_id(video_id_or_url)
    if not video_id:
        # URLでなければそのままIDとして使用
        video_id = video_id_or_url
    
    print(f"処理開始: {video_id}")
    
    # 1. 動画情報を取得
    print("  動画情報を取得中...")
    video_info = tool.get_video_info(video_id)
    print(f"  タイトル: {video_info['title']}")
    print(f"  チャンネル: {video_info['channel']}")
    
    # 2. 文字起こしを取得
    print("  文字起こしを取得中...")
    transcript = tool.get_transcript(video_id)
    
    if not transcript:
        raise ValueError("文字起こしが取得できませんでした")
    
    print(f"  文字起こし完了: {len(transcript)}行")
    
    # 3. JSONに保存
    if not dry_run:
        transcript_path = save_transcript_json(video_id, video_info, transcript, transcripts_dir)
        print(f"  文字起こし保存: {transcript_path}")
    else:
        transcript_path = None
        print("  [dry-run] 文字起こし保存をスキップ")
    
    # 4. 要約を生成
    print(f"  要約を生成中 (Gemini 2.0 Flash)...")
    
    # 文字起こしテキストを連結
    transcript_text = "\n".join([f"[{item['start']:.1f}] {item['text']}" for item in transcript])
    
    # 一時的にMarkdownファイルを作成して要約生成
    temp_md = tool.create_markdown(video_info, transcript, f"https://www.youtube.com/watch?v={video_id}")
    temp_path = transcripts_dir / f"_temp_{video_id}.md"
    
    if not dry_run:
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(temp_md)
        
        summary, _ = tool.generate_summary_with_openrouter(str(temp_path), video_info.get('description', ''))
        
        # 一時ファイル削除
        temp_path.unlink(missing_ok=True)
        
        print(f"  要約完了: {len(summary)}文字")
    else:
        summary = "[dry-run] 要約はスキップされました"
        print("  [dry-run] 要約生成をスキップ")
    
    # 5. Markdownに保存
    if not dry_run:
        summary_path = save_summary_markdown(video_id, video_info, summary, summaries_dir)
        print(f"  要約保存: {summary_path}")
    else:
        summary_path = None
        print("  [dry-run] 要約保存をスキップ")
    
    # 6. 状態を更新
    if not dry_run:
        update_state(state_path, video_id, video_info)
        print("  状態を更新しました")
    else:
        print("  [dry-run] 状態更新をスキップ")
    
    return {
        "video_id": video_id,
        "title": video_info["title"],
        "channel": video_info["channel"],
        "transcript_path": str(transcript_path) if transcript_path else None,
        "summary_path": str(summary_path) if summary_path else None,
    }


def main():
    parser = argparse.ArgumentParser(description="動画を処理して要約を生成")
    parser.add_argument("video_id", help="YouTube動画IDまたはURL")
    parser.add_argument("--model", default="google/gemini-2.0-flash-001", help="使用するモデル")
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
    openrouter_api_key = api_keys.get("openrouter_api_key")
    
    if not youtube_api_key:
        print("エラー: YouTube API キーが設定されていません")
        return 1
    
    if not openrouter_api_key:
        print("エラー: OpenRouter API キーが設定されていません")
        return 1
    
    # ツール初期化
    tool = YouTubeTranscriptToolOpenRouter(
        youtube_api_key=youtube_api_key,
        openrouter_api_key=openrouter_api_key,
        model=args.model,
        output_dir=str(project_root),
        prompt_template=args.prompt_template,
    )
    
    print(f"モデル: {args.model}")
    print(f"テンプレート: {args.prompt_template}\n")
    
    try:
        result = process_video(
            args.video_id,
            tool,
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
