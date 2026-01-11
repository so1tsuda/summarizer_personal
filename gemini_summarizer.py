#!/usr/bin/env python3
"""
Google AI Studio Gemini API を使用した要約生成モジュール
- 新しい google-genai SDK を使用
- Gemini 2.5 Flash モデルをサポート
"""

import os
import time
import json
from typing import Dict, Optional, Tuple
from pathlib import Path

from google import genai


class GeminiSummarizer:
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        prompt_template: str = "blog_article",
        config_dir: Optional[str] = None
    ):
        """
        Gemini Summarizer の初期化
        
        Args:
            api_key: Google AI Studio API Key (GEMINI_API_KEY)
            model_name: 使用するGeminiモデル
            prompt_template: プロンプトテンプレート名
            config_dir: model_configs.json のディレクトリ
        """
        self.api_key = api_key
        self.model_name = model_name
        self.prompt_template = prompt_template
        
        # 新SDK: Clientを初期化
        self.client = genai.Client(api_key=api_key)
        
        # プロンプト設定の読み込み
        if config_dir is None:
            config_dir = Path(__file__).parent
        
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
                
                # 新SDK: client.models.generate_content を使用
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[system_message, user_prompt],
                    config={
                        "temperature": 0.3,
                        "max_output_tokens": 8192,
                    }
                )
                
                summary = response.text
                
                # メタデータ
                metadata = {
                    "model": self.model_name,
                    "prompt_template": self.prompt_template,
                    "attempt": attempt + 1,
                }
                
                print(f"  ✅ 要約完了: {len(summary)}文字")
                return summary, metadata
            
            except Exception as e:
                print(f"  ❌ エラー (試行 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # exponential backoff
                    print(f"  {wait_time}秒後にリトライします...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"要約生成に失敗しました: {e}")
        
        raise Exception("要約生成に失敗しました（リトライ上限）")


def load_api_key() -> str:
    """
    .env または環境変数から Gemini API Key を読み込む
    新SDK用: GEMINI_API_KEY を優先、なければ GOOGLE_AI_API_KEY をフォールバック
    """
    try:
        from dotenv import load_dotenv
        
        script_dir = Path(__file__).parent
        env_path = script_dir / ".env"
        
        if env_path.exists():
            load_dotenv(env_path)
        
        # 新しい環境変数名を優先
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY", "")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY が設定されていません")
        
        return api_key
    
    except ImportError:
        print("警告: python-dotenvがインストールされていません")
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY が設定されていません")
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
