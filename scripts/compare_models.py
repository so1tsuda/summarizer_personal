#!/usr/bin/env python3
"""
複数のモデルで要約を比較するスクリプト
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from youtube_transcript_tool import YouTubeTranscriptToolOpenRouter, load_api_keys


def compare_models(
    video_id_or_url: str,
    models: List[str],
    output_path: Path,
    prompt_template: str = "supereditor"
):
    """
    複数のモデルで同じ動画を要約して比較
    
    Args:
        video_id_or_url: YouTube動画IDまたはURL
        models: 比較するモデルのリスト
        output_path: 出力ファイルパス
        prompt_template: プロンプトテンプレート
    """
    # APIキー読み込み
    api_keys = load_api_keys()
    youtube_api_key = api_keys.get("youtube_api_key")
    openrouter_api_key = api_keys.get("openrouter_api_key")
    
    if not youtube_api_key or not openrouter_api_key:
        raise ValueError("APIキーが設定されていません")
    
    # 最初のツールインスタンスで動画情報と文字起こしを取得
    print(f"動画情報を取得中...")
    tool = YouTubeTranscriptToolOpenRouter(
        youtube_api_key=youtube_api_key,
        openrouter_api_key=openrouter_api_key,
        model=models[0],
        output_dir=str(project_root),
        prompt_template=prompt_template,
    )
    
    # URLからvideo_idを抽出
    video_id = tool.extract_video_id(video_id_or_url)
    if not video_id:
        video_id = video_id_or_url
    
    # 動画情報取得
    video_info = tool.get_video_info(video_id)
    print(f"タイトル: {video_info['title']}")
    print(f"チャンネル: {video_info['channel']}")
    
    # 文字起こし取得
    print(f"文字起こしを取得中...")
    transcript = tool.get_transcript(video_id)
    if not transcript:
        raise ValueError("文字起こしが取得できませんでした")
    
    print(f"文字起こし完了: {len(transcript)}行\n")
    
    # 一時的にMarkdownファイルを作成
    temp_dir = project_root / "data" / "transcripts"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_md_path = temp_dir / f"_temp_{video_id}.md"
    temp_md = tool.create_markdown(video_info, transcript, f"https://www.youtube.com/watch?v={video_id}")
    
    with open(temp_md_path, 'w', encoding='utf-8') as f:
        f.write(temp_md)
    
    # 各モデルで要約生成
    summaries = {}
    
    for i, model in enumerate(models, 1):
        print(f"[{i}/{len(models)}] {model} で要約生成中...")
        
        # モデルごとにツールを再初期化
        model_tool = YouTubeTranscriptToolOpenRouter(
            youtube_api_key=youtube_api_key,
            openrouter_api_key=openrouter_api_key,
            model=model,
            output_dir=str(project_root),
            prompt_template=prompt_template,
        )
        
        try:
            summary, _ = model_tool.generate_summary_with_openrouter(
                str(temp_md_path),
                video_info.get('description', '')
            )
            summaries[model] = summary
            print(f"  ✅ 完了 ({len(summary)}文字)\n")
        except Exception as e:
            print(f"  ❌ エラー: {e}\n")
            summaries[model] = f"エラー: {e}"
    
    # 一時ファイル削除
    temp_md_path.unlink(missing_ok=True)
    
    # 比較レポート作成
    print(f"比較レポートを作成中...")
    create_comparison_report(video_info, summaries, output_path)
    print(f"✅ 完了: {output_path}")


def create_comparison_report(video_info: Dict, summaries: Dict[str, str], output_path: Path):
    """比較レポートをMarkdownで作成"""
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # ヘッダー
        f.write(f"# モデル比較レポート\n\n")
        f.write(f"**動画タイトル**: {video_info['title']}\n\n")
        f.write(f"**チャンネル**: {video_info['channel']}\n\n")
        f.write(f"**YouTube URL**: https://www.youtube.com/watch?v={video_info.get('video_id', '')}\n\n")
        f.write(f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"---\n\n")
        
        # 目次
        f.write(f"## 目次\n\n")
        for i, model in enumerate(summaries.keys(), 1):
            model_anchor = model.replace('/', '-').replace('.', '-')
            f.write(f"{i}. [{model}](#{model_anchor})\n")
        f.write(f"\n---\n\n")
        
        # 各モデルの要約
        for model, summary in summaries.items():
            model_anchor = model.replace('/', '-').replace('.', '-')
            f.write(f"## {model}\n\n")
            f.write(f"<a id=\"{model_anchor}\"></a>\n\n")
            f.write(f"**文字数**: {len(summary)}文字\n\n")
            f.write(f"{summary}\n\n")
            f.write(f"---\n\n")


def main():
    parser = argparse.ArgumentParser(description="複数のモデルで要約を比較")
    parser.add_argument("video_id", help="YouTube動画IDまたはURL")
    parser.add_argument(
        "--models",
        nargs="+",
        default=[
            "google/gemini-2.0-flash-lite-001",
            "google/gemini-2.0-flash-001",
            "qwen/qwen-turbo",
            "qwen/qwen3-next-80b-a3b-instruct",
        ],
        help="比較するモデルのリスト"
    )
    parser.add_argument(
        "--output",
        default="data/model_comparison.md",
        help="出力ファイルパス"
    )
    parser.add_argument(
        "--prompt-template",
        default="supereditor",
        choices=["strategist", "supereditor"],
        help="プロンプトテンプレート"
    )
    
    args = parser.parse_args()
    
    output_path = project_root / args.output
    
    print(f"=== モデル比較開始 ===")
    print(f"動画: {args.video_id}")
    print(f"モデル数: {len(args.models)}")
    print(f"出力先: {output_path}\n")
    
    try:
        compare_models(
            args.video_id,
            args.models,
            output_path,
            args.prompt_template
        )
        return 0
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
