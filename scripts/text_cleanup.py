import re
import os
from typing import Optional

def remove_fillers(text: str) -> str:
    """
    意味を持たないフィラー（つなぎ言葉）を除去する
    """
    # 英語のフィラー (単語境界 \b を使用)
    text = re.sub(r'\b(um|uh|ah|er|hmm)\b', '', text, flags=re.IGNORECASE)
    
    # 日本語のフィラー
    text = re.sub(r'(?<=[\u3000-\u303F])(えー|あのー|んー)(?=[\u3000-\u303F])', '', text)
    
    return text

def remove_stutter(text: str) -> str:
    """
    吃音（繰り返しの単語）を除去する
    """
    # 英単語の繰り返し
    text = re.sub(r'\b(\w+)( \1\b)+', r'\1', text, flags=re.IGNORECASE)
    
    return text

def clean_transcript_text(transcript_content: str, keep_timestamps: bool = False) -> str:
    """
    AI要約用に文字起こしコンテンツを最適化する
    """
    # 1. 文字起こしセクションの抽出
    lines = transcript_content.split('\n')
    transcript_start = -1
    for i, line in enumerate(lines):
        if "## 文字起こし" in line or "# 文字起こし" in line:
            transcript_start = i + 1
            break
    
    if transcript_start != -1:
        raw_text = '\n'.join(lines[transcript_start:])
    else:
        raw_text = transcript_content

    clean_text = raw_text

    # 2. タイムスタンプと装飾の除去
    if not keep_timestamps:
        # **[HH:MM:SS]** 形式
        clean_text = re.sub(r'\*\*\[\d{2}:\d{2}:\d{2}(?:\.\d+)?\]\*\*\s*', '', clean_text)
        # [HH:MM:SS] 形式
        clean_text = re.sub(r'\[\d{2}:\d{2}:\d{2}\]\s*', '', clean_text)
        # [0.0] or [123.45] 形式
        clean_text = re.sub(r'\[\d+(?:\.\d+)?\]\s*', '', clean_text)
    
    # 画像・リンク除去
    clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', clean_text)
    clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text)

    # 3. フィラーと吃音の除去
    clean_text = remove_fillers(clean_text)
    clean_text = remove_stutter(clean_text)

    # 4. トークン圧縮ロジック
    clean_text = re.sub(r'\s+', ' ', clean_text)

    # 5. 話者区切り（>>）の復元
    clean_text = clean_text.replace(' >>', '\n\n>>')
    
    return clean_text.strip()

def get_cleaned_path(original_path: str) -> str:
    """
    元のパスからクリーンアップ済みテキストのパスを生成 (video_id.json -> video_id_cleaned.txt)
    """
    base, _ = os.path.splitext(original_path)
    return f"{base}_cleaned.txt"

def save_text_to_file(text: str, file_path: str) -> bool:
    """
    テキストを指定されたパスに保存
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"  ⚠️ ファイル保存に失敗 ({file_path}): {e}")
        return False
