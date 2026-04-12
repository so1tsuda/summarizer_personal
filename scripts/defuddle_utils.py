#!/usr/bin/env python3
"""
Defuddle CLI を使って YouTube ページから Markdown 文字起こしを取得する補助関数。
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def get_defuddle_path(original_path: str) -> str:
    """
    元のパスから defuddle Markdown のパスを生成する (video_id.json -> video_id_defuddle.md)
    """
    path = Path(original_path)
    return str(path.with_name(f"{path.stem}_defuddle.md"))


def fetch_defuddle_markdown(video_id: str, output_path: str, timeout: int = 180) -> Optional[str]:
    """
    defuddle CLI を呼び出して YouTube ページを Markdown として保存する。
    成功時は output_path を返し、失敗時は None を返す。
    """
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        result = subprocess.run(
            ["defuddle", "parse", youtube_url, "--md", "-o", output_path],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.stdout.strip():
            print(f"  {result.stdout.strip()}")
        return output_path
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        print(f"  ⚠️ defuddle取得失敗: {error}")
        return None
    except Exception as exc:
        print(f"  ⚠️ defuddle取得失敗: {exc}")
        return None

