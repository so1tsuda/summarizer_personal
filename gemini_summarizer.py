#!/usr/bin/env python3
"""
Google AI Studio Gemini API を使用した要約生成モジュール
- OpenRouterの代わりにGoogle Gemini APIを使用
- 無料枠を活用してコストを削減
"""

import os
import time
import json
from typing import Dict, Optional, Tuple
from pathlib import Path

import google.generativeai as genai


class GeminiSummarizer:
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        prompt_template: str = "blog_article",
        config_dir: Optional[str] = None
    ):
        """
        Gemini Summarizer の初期化
        
        Args:
            api_key: Google AI Studio API Key
            model_name: 使用するGeminiモデル
            prompt_template: プロンプトテンプレート名
            config_dir: model_configs.json のディレクトリ
        """
        self.api_key = api_key
        self.model_name = model_name
        self.prompt_template = prompt_template
        
        # Gemini API設定
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # プロンプト設定の読み込み
        if config_dir is None:
            config_dir = Path(__file__).parent.parent
        
        config_path = Path(config_dir) / "model_configs.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.prompt_config = self.config.get("prompt_templates", {}).get(prompt_template, {})
    
    def generate_summary(
        self,
        transcript_text: str,
        video_description: str = "",
        max_retries: int = 3
    ) -> Tuple[str, Dict]:
        """
        文字起こしから要約を生成
        
        Args:
            transcript_text: 文字起こしテキスト
            video_description: 動画の説明文
            max_retries: リトライ回数
        
        Returns:
            (要約テキスト, メタデータ)
        """
        # プロンプト構築
        system_message = self.prompt_config.get("system_message", "You are a helpful assistant.")
        tone_instructions = "\n".join(self.prompt_config.get("tone_instructions", []))
        output_instructions = "\n".join(self.prompt_config.get("output_instructions", []))
        
        user_prompt = f"""
# === Tone & Manner ===
{tone_instructions}

# === Output Instructions ===
{output_instructions}

# === Video Description ===
{video_description}

# === Transcript ===
{transcript_text}
"""
        
        # リトライループ
        for attempt in range(max_retries):
            try:
                print(f"  [Gemini {self.model_name}] 要約生成中... (試行 {attempt + 1}/{max_retries})")
                
                # Gemini API呼び出し
                response = self.model.generate_content(
                    [system_message, user_prompt],
                    generation_config=genai.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=8192,
                    )
                )
                
                summary = response.text
                
                # メタデータ
                metadata = {
                    "model": self.model_name,
                    "prompt_template": self.prompt_template,
                    "attempt": attempt + 1,
                    "finish_reason": response.candidates[0].finish_reason if response.candidates else None,
                }
                
                print(f"  要約完了: {len(summary)}文字")
                return summary, metadata
            
            except Exception as e:
                print(f"  エラー (試行 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # exponential backoff
                    print(f"  {wait_time}秒後にリトライします...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"要約生成に失敗しました: {e}")
        
        raise Exception("要約生成に失敗しました（リトライ上限）")


def load_api_key() -> str:
    """
    .env または環境変数から Google AI API Key を読み込む
    """
    try:
        from dotenv import load_dotenv
        
        script_dir = Path(__file__).parent.parent
        env_path = script_dir / ".env"
        
        if env_path.exists():
            load_dotenv(env_path)
        
        api_key = os.getenv("GOOGLE_AI_API_KEY", "")
        
        if not api_key:
            raise ValueError("GOOGLE_AI_API_KEY が設定されていません")
        
        return api_key
    
    except ImportError:
        print("警告: python-dotenvがインストールされていません")
        api_key = os.getenv("GOOGLE_AI_API_KEY", "")
        if not api_key:
            raise ValueError("GOOGLE_AI_API_KEY が設定されていません")
        return api_key


if __name__ == "__main__":
    # テスト用
    api_key = load_api_key()
    summarizer = GeminiSummarizer(api_key)
    
    test_transcript = """
    [0.0] こんにちは、今日はAIについて話します。
    [5.0] AIは私たちの生活を大きく変えています。
    [10.0] 特に自然言語処理の分野では目覚ましい進歩があります。
    """
    
    summary, metadata = summarizer.generate_summary(test_transcript, "AIについての動画")
    print("\n=== 要約 ===")
    print(summary)
    print("\n=== メタデータ ===")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
