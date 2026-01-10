#!/usr/bin/env python3
"""
YouTube動画から文字起こしを取得し、Obsidian用のMarkdownファイルを作成するツール（OpenRouter版）
"""

import os
import re
import json
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# OpenAIライブラリ（OpenRouterはOpenAI API互換）
from openai import OpenAI

# YouTube API関連
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Setting management
from config_manager import ConfigManager, PromptBuilder

# YouTube Transcript API
from youtube_transcript_api import YouTubeTranscriptApi

def load_api_keys():
    """
    .envファイルまたは環境変数からAPIキーを読み込む
    """
    try:
        from dotenv import load_dotenv
        
        # .envファイルを読み込み
        script_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(script_dir, ".env")
        
        if os.path.exists(env_path):
            load_dotenv(env_path)
        
        return {
            "youtube_api_key": os.getenv("YOUTUBE_API_KEY", ""),
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        }
    except ImportError:
        print("警告: python-dotenvがインストールされていません")
        return {
            "youtube_api_key": os.getenv("YOUTUBE_API_KEY", ""),
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        }
    except Exception as e:
        print(f"警告: APIキーの読み込みに失敗しました: {e}")
        return {}

class YouTubeTranscriptToolOpenRouter:
    def __init__(self, youtube_api_key: str, openrouter_api_key: str,
                 model: str = "google/gemini-2.5-flash", output_dir: str = ".",
                 config_dir: Optional[str] = None, use_stream: bool = False,
                 prompt_template: str = "strategist",
                 chronological_model: str = "qwen/qwen-turbo"):
        """
        ツールの初期化

        Args:
            youtube_api_key: YouTube Data APIのキー
            openrouter_api_key: OpenRouter APIのキー
            model: 使用するOpenRouterモデル (Insight用)
            output_dir: 出力ディレクトリ
            config_dir: 設定ファイルのディレクトリ
            use_stream: ストリーミング応答を使用するかどうか（デバッグ用）
            prompt_template: プロンプトテンプレート名
            chronological_model: 時系列サマリー用のモデル
        """
        self.youtube_api_key = youtube_api_key
        self.openrouter_api_key = openrouter_api_key
        self.model = model
        self.chronological_model = chronological_model
        self.output_dir = output_dir
        self.use_stream = use_stream  # デバッグ用フラグ
        self.prompt_template = prompt_template
        self.youtube = build('youtube', 'v3', developerKey=youtube_api_key)

        # 設定管理の初期化
        self.config_manager = ConfigManager(config_dir)
        self.prompt_builder = PromptBuilder(self.config_manager)

        # モデル設定の取得
        try:
            self.config = self.config_manager.get_model_config(model)
            self.api_settings = self.config_manager.get_api_setting('openrouter')
        except ValueError as e:
            print(f"警告: {e}")
            # デフォルト設定を適用
            self.config = {
                "max_tokens": 1500,
                "temperature": 0.3,
                "max_content_length": 12000,
                "description": "デフォルト設定",
                "prompt_template": "strategist"
            }
            self.api_settings = {
                "base_url": "https://openrouter.ai/api/v1",
                "timeout": 60,
                "max_retries": 3,
                "headers": {
                    "HTTP-Referer": "https://github.com/anthropics/anthropic-sdk-python",
                    "X-Title": "YouTube Transcript Tool"
                }
            }

        # OpenAIクライアントの初期化（OpenRouter用）
        self.client = OpenAI(
            api_key=self.openrouter_api_key,
            base_url=self.api_settings["base_url"],
            timeout=self.api_settings["timeout"]
        )

    def get_available_models(self) -> List[str]:
        """
        利用可能なモデルの一覧を取得
        """
        return self.config_manager.get_available_models()

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        YouTube URLから動画IDを抽出

        Args:
            url: YouTubeのURL

        Returns:
            動画ID（抽出できない場合はNone）
        """
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/watch\?.*v=([^&\n?#]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def get_video_info(self, video_id: str) -> Dict:
        """
        YouTube動画の基本情報を取得

        Args:
            video_id: YouTube動画ID

        Returns:
            動画情報の辞書
        """
        try:
            response = self.youtube.videos().list(
                part='snippet,contentDetails',
                id=video_id
            ).execute()

            if not response['items']:
                raise ValueError(f"動画が見つかりません: {video_id}")

            video = response['items'][0]
            return {
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'channel': video['snippet']['channelTitle'],
                'published_at': video['snippet']['publishedAt'],
                'duration': video['contentDetails']['duration'],
                'thumbnail': video['snippet']['thumbnails']['high']['url']
            }
        except HttpError as e:
            raise Exception(f"YouTube APIエラー: {e}")

    def get_transcript(self, video_id: str) -> List[Dict]:
        """
        YouTube動画の文字起こしを取得

        Args:
            video_id: YouTube動画ID

        Returns:
            文字起こしデータのリスト
        """
        try:
            print(f"字幕を取得中 (ID: {video_id})...")

            # 優先順位付き言語リスト
            languages = ['ja', 'en', 'en-US', 'en-GB']

            # 字幕を取得（優先言語で見つからない場合は自動生成などをフォールバック）
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id)
            
            try:
                # 手動字幕を優先
                transcript_obj = transcript_list.find_manually_created_transcript(languages)
                print(f"  手動字幕が見つかりました: {transcript_obj.language}")
            except:
                try:
                    # なければ自動生成字幕
                    transcript_obj = transcript_list.find_generated_transcript(languages)
                    print(f"  自動字幕が見つかりました: {transcript_obj.language}")
                except:
                    # それでもなければ利用可能な最初の字幕
                    transcript_obj = next(iter(transcript_list))
                    print(f"  利用可能な最初の字幕を使用します: {transcript_obj.language}")

            transcript = transcript_obj.fetch()

            # 結果を整形
            formatted_transcript = []
            for entry in transcript:
                # FetchedTranscriptSnippet オブジェクトを処理
                formatted_transcript.append({
                    'start': entry.start,
                    'duration': entry.duration,
                    'text': entry.text.strip()
                })

            print(f"  文字起こし完了: {len(formatted_transcript)}行")
            return formatted_transcript

        except Exception as e:
            print(f"文字起こしの取得に失敗しました: {e}")
            return []

    def format_timestamp(self, seconds: float) -> str:
        """
        秒数をHH:MM:SS形式に変換

        Args:
            seconds: 秒数

        Returns:
            HH:MM:SS形式のタイムスタンプ
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def create_markdown(self, video_info: Dict, transcript: List[Dict], url: str) -> str:
        """
        文字起こしをObsidian用のMarkdown形式に変換

        Args:
            video_info: 動画情報
            transcript: 文字起こしデータ
            url: YouTube動画のURL

        Returns:
            Markdown形式の文字列
        """
        title = video_info['title']
        channel = video_info['channel']
        published = video_info['published_at'][:10]  # 日付部分のみ
        thumbnail = video_info['thumbnail']
        description = video_info.get('description', '').strip()

        # サムネイルの埋め込み
        markdown_content = f"# {title}\n\n"
        markdown_content += f"![{title}]({thumbnail})\n\n"

        # 動画の埋め込み
        video_id = self.extract_video_id(url)
        markdown_content += f"![](https://www.youtube.com/watch?v={video_id})\n\n"

        # メタ情報
        markdown_content += "## メタ情報\n\n"
        markdown_content += f"- **チャンネル**: {channel}\n"
        markdown_content += f"- **公開日**: {published}\n"
        markdown_content += f"- **URL**: [{url}]({url})\n"
        markdown_content += f"- **要約モデル**: {self.model}\n\n"

        # 動画概要欄（存在する場合）
        if description:
            markdown_content += "## 動画概要\n\n"
            # 概要欄の整形：改行を維持し、リンクなどをMarkdown形式に変換
            formatted_description = self._format_description(description)
            markdown_content += f"{formatted_description}\n\n"

        # 文字起こし
        markdown_content += "## 文字起こし\n\n"

        for item in transcript:
            timestamp = self.format_timestamp(item['start'])
            text = item['text']
            markdown_content += f"**[{timestamp}]** {text}\n\n"

        return markdown_content

    def _format_description(self, description: str) -> str:
        """
        動画概要欄をMarkdown形式に整形する

        Args:
            description: 生の概要欄テキスト

        Returns:
            整形されたMarkdownテキスト
        """
        try:
            # 改行を維持
            lines = description.split('\n')
            formatted_lines = []

            for line in lines:
                line = line.strip()
                if not line:
                    # 空行はそのまま維持
                    formatted_lines.append("")
                elif line.startswith('#'):
                    # 見出しの場合はエスケープ
                    formatted_lines.append(f"\\{line}")
                elif line.startswith('*') or line.startswith('-'):
                    # 箇条書きの場合はそのまま維持
                    formatted_lines.append(line)
                elif line.startswith(('http://', 'https://')):
                    # URLはMarkdownリンクに変換
                    formatted_lines.append(f"[{line}]({line})")
                else:
                    # その他のテキストはそのまま
                    formatted_lines.append(line)

            return '\n'.join(formatted_lines)

        except Exception as e:
            print(f"概要欄の整形に失敗: {e}")
            # 失敗した場合は元のテキストを返す
            return description

    def save_markdown(self, content: str, filename: str) -> str:
        """
        Markdownコンテンツをファイルに保存

        Args:
            content: Markdownコンテンツ
            filename: ファイル名（.mdなし）

        Returns:
            保存したファイルのパス
        """
        # ファイル名から不正な文字を除去
        safe_filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        safe_filename = safe_filename[:100]  # 長さを制限

        filepath = os.path.join(self.output_dir, f"{safe_filename}.md")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def _remove_fillers(self, text: str) -> str:
        """
        意味を持たないフィラー（つなぎ言葉）を除去する
        ※誤爆を防ぐため、明らかにフィラーとわかるものに限定
        """
        # 英語のフィラー (単語境界 \b を使用)
        # um, uh, ah, er, hmm
        text = re.sub(r'\b(um|uh|ah|er|hmm)\b', '', text, flags=re.IGNORECASE)
        
        # 日本語のフィラー（文脈依存が強いため慎重に）
        # 「えー」「あのー」などは長音が含まれることが多い
        text = re.sub(r'(?<=[\u3000-\u303F])(えー|あのー|んー)(?=[\u3000-\u303F])', '', text)
        
        return text

    def _remove_stutter(self, text: str) -> str:
        """
        吃音（繰り返しの単語）を除去する
        例: "I I I think" -> "I think"
        """
        # 英単語の繰り返し (2回以上)
        # \b(\w+)\s+\1\b -> "word word"
        text = re.sub(r'\b(\w+)( \1\b)+', r'\1', text, flags=re.IGNORECASE)
        
        return text

    def _format_description(self, description: str) -> str:
        """
        動画概要欄を整形し、SNSリンクや定型文以降をカットする
        """
        try:
            lines = description.split('\n')
            formatted_lines = []
            
            # 終了判定用のキーワード（これらが出たら以降はカット）
            cutoff_keywords = [
                "---", "___", "===", 
                "Follow us", "Subscribe", "Social Media", 
                "Twitter", "Instagram", "Facebook", "TikTok",
                "Copyright", "All rights reserved", 
                "Music by", "Gear used",
                "チャンネル登録", "SNS", "フォロー"
            ]

            line_count = 0
            max_lines = 20 # 最初の20行だけ読めば十分なことが多い

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # カットオフキーワードが含まれていたら終了
                if any(keyword in line for keyword in cutoff_keywords):
                    formatted_lines.append("\n（※以降の定型文はカットされました）")
                    break
                
                # URLだけの行は情報量が低いのでスキップしてもいいが、
                # 重要な参照リンクの場合もあるので残す。ただしMarkdown化する。
                if line.startswith(('http://', 'https://')):
                     formatted_lines.append(f"[{line}]({line})")
                else:
                    formatted_lines.append(line)
                
                line_count += 1
                if line_count >= max_lines:
                    formatted_lines.append("\n（※長すぎるため以降は省略）")
                    break

            return '\n'.join(formatted_lines)

        except Exception as e:
            print(f"概要欄の整形に失敗: {e}")
            return description

    def _clean_transcript_for_summary(self, transcript_content: str, keep_timestamps: bool = False) -> str:
        """
        AI要約用に文字起こしコンテンツを最適化する（トークン節約版）
        1. タイムスタンプ除去 (keep_timestamps=Trueの場合は保持)
        2. 無駄な改行を削除して文章を連結
        3. 話者（>>）の変わり目のみ改行を入れる
        """
        try:
            # 1. 文字起こしセクションの抽出（既存ロジック）
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
            
            # 画像・リンク除去
            clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', clean_text)
            clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text)

            # 3. フィラーと吃音の除去（トークン削減）
            # 空白圧縮の「前」に行うことで、除去後に残った微妙な空白も次のステップで消せる
            clean_text = self._remove_fillers(clean_text)
            clean_text = self._remove_stutter(clean_text)

            # 4. 【重要】トークン圧縮ロジック
            # すべての改行と連続する空白を、一旦シングルスペースに置換する
            # これで "I \n was like" が "I was like" になり、文が繋がる
            clean_text = re.sub(r'\s+', ' ', clean_text)

            # 5. 話者区切り（>>）の前には改行を入れて構造を復元する
            # " text. >> Next speaker" -> " text.\n\n>> Next speaker"
            clean_text = clean_text.replace(' >>', '\n\n>>')
            
            # 先頭に >> がある場合の微調整
            clean_text = clean_text.strip()
            print(clean_text) # Output for debugging
            print(f"文字起こしを圧縮完了: {len(clean_text)}文字")

            return clean_text

        except Exception as e:
            print(f"文字起こしのクリーンアップに失敗: {e}")
            return transcript_content

    def _contains_unwanted_characters(self, text: str, target_lang: str = "ja") -> Tuple[bool, str]:
        """
        指定された言語に対して不適切な文字が含まれているかチェックする
        
        Args:
            text: チェック対象のテキスト
            target_lang: ターゲット言語 ('ja' or 'en')
            
        Returns:
            Tuple[bool, str]: (不適切な文字が含まれているか, 検出された理由)
        """
        import re
        from typing import Tuple
        
        # 韓国語（ハングル）の範囲: U+AC00-U+D7A3
        hangul_pattern = re.compile(r'[\uAC00-\uD7A3]')
        
        if hangul_pattern.search(text):
            return True, "Korean (Hangul) characters detected"
            
        if target_lang == "en":
            # 英語の場合、日本語（ひらがな、カタカナ、漢字）が含まれていないかチェック
            # ひらがな: U+3040-U+309F
            # カタカナ: U+30A0-U+30FF
            # 漢字: U+4E00-U+9FFF
            japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]')
            if japanese_pattern.search(text):
                return True, "Japanese characters detected in English summary"
                
        return False, ""

    def _generate_single_part(self, model: str, template_name: str, cleaned_content: str, video_description: str) -> str:
        """
        単一のパート（InsightまたはChronological）を生成するヘルパーメソッド
        """
        try:
            # テンプレートの取得
            prompt_template_dict = self.config_manager.get_prompt_template(template_name)
            target_lang = "en" if "_en" in template_name else "ja"
            
            # System Message
            system_prompt = prompt_template_dict.get("system_message", "You are a helpful assistant.")
            
            # User Message Construction
            tone_instructions = "\n".join(prompt_template_dict.get("tone_instructions", []))
            output_instructions = "\n".join(prompt_template_dict.get("output_instructions", []))
            
            user_prompt = f"""
# === Tone & Manner ===
{tone_instructions}

# === Output Instructions ===
{output_instructions}

# === Video Description ===
{video_description}

# === Transcript ===
{cleaned_content}
"""

            # リトライループ
            max_retries = 3
            current_try = 0
            
            while current_try < max_retries:
                current_try += 1
                print(f"  [{model}] 生成試行 {current_try}/{max_retries}...")
                
                current_user_prompt = user_prompt
                if current_try > 1:
                    if target_lang == "ja":
                        current_user_prompt += "\n\nIMPORTANT: Output MUST be in Japanese. Do NOT use Korean characters."
                    else:
                        current_user_prompt += "\n\nIMPORTANT: Output MUST be in English. Do NOT use Japanese or Korean characters."

                # APIリクエスト
                # モデル設定の取得（max_tokensなど）
                try:
                    model_config = self.config_manager.get_model_config(model)
                    max_tokens = model_config.get('max_tokens', 4096)
                    temperature = model_config.get('temperature', 0.3)
                except:
                    # デフォルトフォールバック
                    max_tokens = 4096
                    temperature = 0.3

                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": current_user_prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True
                )

                # ストリーミングレスポンスの処理
                summary = ""
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        summary += content
                        # print(content, end="", flush=True) # Suppressed

                # 言語チェック
                has_unwanted, reason = self._contains_unwanted_characters(summary, target_lang)
                
                if has_unwanted:
                    print(f"  ⚠️ 警告: 不適切な文字が検出されました ({reason})。リトライします。")
                    if current_try == max_retries:
                        print("  ❌ 最大試行回数に達しました。不完全な要約を返します。")
                    else:
                        continue
                
                return summary

            return summary # 最大試行回数到達時

        except Exception as e:
            print(f"  ❌ 生成エラー ({model}): {e}")
            return f"生成エラー ({model}): {str(e)}"

    def generate_summary_with_openrouter(self, filepath: str, video_description: str = "") -> Tuple[str, str]:
        """
        OpenRouterを使って要約を生成（OpenAIライブラリ使用）
        言語チェックとリトライロジックを含む
        """
        try:
            # 文字起こしファイルを読み込み
            with open(filepath, 'r', encoding='utf-8') as f:
                transcript_content = f.read()

            # 文字起こしをクリーンアップ（トークン節約のため）
            # 1. Insight用: タイムスタンプなし（トークン節約）
            cleaned_content_insight = self._clean_transcript_for_summary(transcript_content, keep_timestamps=False)
            
            # プロンプトテンプレートが "supereditor" の場合のみ分割生成を行う
            if self.prompt_template == "supereditor":
                print(f"✨ Dual Model Generation Mode")
                print(f"  1. Insight (I & II): {self.model}")
                print(f"  2. Chronological (III): {self.chronological_model}")

                # 1. Insight Generation
                insight_part = self._generate_single_part(
                    self.model, 
                    "supereditor_insight_v2", 
                    cleaned_content_insight, 
                    video_description
                )

                # 2. Chronological Summary Generation
                # 時系列サマリー用: タイムスタンプあり
                cleaned_content_chronological = self._clean_transcript_for_summary(transcript_content, keep_timestamps=True)
                
                chronological_part = self._generate_single_part(
                    self.chronological_model, 
                    "supereditor_chronological_v2", 
                    cleaned_content_chronological, 
                    video_description
                )

                # 統合
                summary = f"{insight_part}\n\n{chronological_part}"
                
                # 日本語Markdownの強調表示修正
                summary = self._format_japanese_markdown(summary)
                
                print(f"要約完了: {len(summary)}文字")
                return summary, cleaned_content_insight

            else:
                # 従来のカラム（シングルモデル）
                print(f"✨ Single Model Generation Mode: {self.model} ({self.prompt_template})")
                summary = self._generate_single_part(
                    self.model,
                    self.prompt_template,
                    cleaned_content_insight,
                    video_description
                )
                
                # 日本語Markdownの強調表示修正
                summary = self._format_japanese_markdown(summary)

                print(f"要約完了: {len(summary)}文字")
                return summary, cleaned_content_insight

        except Exception as e:
            # APIが利用できない場合は代替要約を返す
            print(f"❌ 要約生成全体エラー: {e}")
            return f"## 要約\n\n※要約の生成に失敗しました: {str(e)}\n\n手動で要約を追加してください。", ""

    def _format_japanese_markdown(self, text: str) -> str:
        """
        日本語Markdownの強調表示の問題を修正する
        **の前または後にスペースがないと上手く強調表示できない問題を解決
        """
        # **の前にスペースが必要なケース
        # "**「" -> " **「"
        text = text.replace("**「", " **「")
        # "**（" -> " **（"
        text = text.replace("**（", " **（")

        # **の後にスペースが必要なケース
        # "」**" -> "」** "
        text = text.replace("」**", "」** ")
        # "）**" -> "）** "
        text = text.replace("）**", "）** ")

        return text

    def add_summary_to_markdown(self, filepath: str, summary: str) -> None:
        """
        生成された要約をMarkdownファイルの先頭に追加

        Args:
            filepath: Markdownファイルのパス
            summary: 追加する要約
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # 最初の見出し（# で始まる行）の位置を探す
            lines = content.split('\n')
            insert_index = 0

            for i, line in enumerate(lines):
                if line.startswith('# '):
                    insert_index = i + 2  # 見出しの後の空行の後に挿入
                    break

            # 要約を挿入
            summary_section = f"{summary}\n\n---\n\n"
            lines.insert(insert_index, summary_section)

            # ファイルに書き戻し
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

        except Exception as e:
            print(f"要約の追加に失敗しました: {e}")

    def process_youtube_url(self, url: str, generate_summary: bool = True) -> str:
        """
        YouTube URLを処理して文字起こしMarkdownを作成

        Args:
            url: YouTube動画のURL
            generate_summary: 要約を生成するかどうか

        Returns:
            Dict[str, Any]: {
                "filepath": 作成されたMarkdownファイルのパス,
                "original_transcript": オリジナルの文字起こしリスト,
                "cleaned_transcript": クリーンアップされた文字起こしテキスト (要約生成時のみ),
                "summary": 要約テキスト (要約生成時のみ)
            }
        """
        print(f"処理中: {url}")

        # 動画IDを抽出
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError("有効なYouTube URLではありません")

        print(f"動画ID: {video_id}")

        # 動画情報を取得
        print("動画情報を取得中...")
        video_info = self.get_video_info(video_id)
        print(f"タイトル: {video_info['title']}")

        # 文字起こしを取得
        print("文字起こしを取得中...")
        transcript = self.get_transcript(video_id)
        print(f"文字起こし完了: {len(transcript)}行")

        # 文字起こしが空の場合の処理
        if not transcript:
            print("警告: 文字起こしが空です。動画に字幕が含まれていない可能性があります。")
            raise ValueError("文字起こしが取得できなかったため、処理を中止します。")

        # Markdownを作成
        print("Markdownファイルを作成中...")
        markdown_content = self.create_markdown(video_info, transcript, url)

        # ファイルに保存
        filepath = self.save_markdown(markdown_content, video_info['title'])
        print(f"保存完了: {filepath}")

        # 要約を生成
        summary = ""
        cleaned_transcript = ""
        
        if generate_summary:
            print(f"OpenRouter ({self.model})で要約を生成中...")
            summary, cleaned_transcript = self.generate_summary_with_openrouter(filepath, video_info.get('description', ''))
            self.add_summary_to_markdown(filepath, summary)
            print("要約を追加しました")

        return {
            "filepath": filepath,
            "original_transcript": transcript,
            "cleaned_transcript": cleaned_transcript,
            "summary": summary
        }


def main():
    parser = argparse.ArgumentParser(description="YouTube動画の文字起こしツール（OpenRouter版）")
    parser.add_argument("url", help="YouTube動画のURL")
    parser.add_argument("-o", "--output", default=".", help="出力ディレクトリ（デフォルト: カレントディレクトリ）")
    parser.add_argument("-y", "--youtube-api-key", help="YouTube Data APIキー（環境変数YOUTUBE_API_KEYからも読み込み）")
    parser.add_argument("-r", "--openrouter-api-key", help="OpenRouter APIキー（環境変数OPENROUTER_API_KEYからも読み込み）")
    parser.add_argument("-m", "--model", default="anthropic/claude-3.5-sonnet",
                       help="使用するOpenRouterモデル（デフォルト: anthropic/claude-3.5-sonnet）")
    parser.add_argument("-p", "--prompt-template", default="strategist", choices=["strategist", "supereditor"],
                       help="プロンプトテンプレート（デフォルト: strategist）")
    parser.add_argument("--list-models", action="store_true", help="利用可能なモデル一覧を表示")
    parser.add_argument("--no-summary", action="store_true", help="要約を生成しない")

    args = parser.parse_args()

    # APIキーの取得
    api_keys = load_api_keys()
    youtube_api_key = args.youtube_api_key or os.getenv("YOUTUBE_API_KEY") or api_keys.get("youtube_api_key")
    openrouter_api_key = args.openrouter_api_key or os.getenv("OPENROUTER_API_KEY") or api_keys.get("openrouter_api_key")

    # モデル一覧表示
    if args.list_models:
        try:
            config_manager = ConfigManager()
            models = config_manager.get_available_models()
            print("利用可能なモデル:")
            for model in models:
                try:
                    model_config = config_manager.get_model_config(model)
                    print(f"  {model} - {model_config.get('description', '説明なし')}")
                except Exception:
                    print(f"  {model}")
        except Exception as e:
            print(f"設定の読み込みに失敗しました: {e}")
        return 0

    if not youtube_api_key:
        print("エラー: YouTube Data APIキーが必要です")
        print("- コマンドライン引数 -y/--youtube-api-key で指定するか")
        print("- 環境変数 YOUTUBE_API_KEY を設定してください")
        print("- または scripts/api_keys.json に youtube_api_key を記述してください")
        return 1

    if not openrouter_api_key:
        print("エラー: OpenRouter APIキーが必要です")
        print("- コマンドライン引数 -r/--openrouter-api-key で指定するか")
        print("- 環境変数 OPENROUTER_API_KEY を設定してください")
        print("- または scripts/api_keys.json に openrouter_api_key を記述してください")
        return 1

    try:
        # ツールを初期化
        tool = YouTubeTranscriptToolOpenRouter(
            youtube_api_key=youtube_api_key,
            openrouter_api_key=openrouter_api_key,
            model=args.model,
            output_dir=args.output,
            prompt_template=args.prompt_template
        )

        print(f"使用モデル: {args.model}")
        if hasattr(tool, 'config') and 'description' in tool.config:
            print(f"説明: {tool.config['description']}")
        print(f"プロンプトテンプレート: {tool.prompt_template}")

        # URLを処理
        result = tool.process_youtube_url(args.url, not args.no_summary)
        filepath = result["filepath"]

        print(f"\n完了! ファイルが作成されました: {filepath}")
        return 0

    except Exception as e:
        print(f"エラー: {e}")
        return 1


if __name__ == "__main__":
    exit(main())