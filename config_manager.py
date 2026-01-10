#!/usr/bin/env python3
"""
設定管理クラス - モデル設定、プロンプトテンプレート、API設定を一元管理
"""

import os
import json
from typing import Dict, Optional, Any


class ConfigManager:
    """設定を一元管理するクラス"""

    def __init__(self, config_dir: Optional[str] = None):
        """
        ConfigManagerの初期化

        Args:
            config_dir: 設定ファイルのディレクトリ（デフォルト: スクリプトディレクトリ）
        """
        if config_dir is None:
            config_dir = os.path.dirname(os.path.abspath(__file__))

        self.config_dir = config_dir
        self._model_configs = None
        self._prompt_templates = None
        self._api_settings = None

    def _load_config(self, filename: str) -> Dict[str, Any]:
        """
        設定ファイルを読み込む

        Args:
            filename: 設定ファイル名

        Returns:
            設定の辞書
        """
        config_path = os.path.join(self.config_dir, filename)

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"設定ファイルのJSON形式が不正です: {e}")
        except Exception as e:
            raise Exception(f"設定ファイルの読み込みに失敗しました: {e}")

    @property
    def model_configs(self) -> Dict[str, Any]:
        """モデル設定を取得"""
        if self._model_configs is None:
            config = self._load_config('model_configs.json')
            self._model_configs = config.get('models', {})
        return self._model_configs

    @property
    def prompt_templates(self) -> Dict[str, Any]:
        """プロンプトテンプレートを取得"""
        if self._prompt_templates is None:
            config = self._load_config('model_configs.json')
            self._prompt_templates = config.get('prompt_templates', {})
        return self._prompt_templates

    @property
    def api_settings(self) -> Dict[str, Any]:
        """API設定を取得"""
        if self._api_settings is None:
            config = self._load_config('model_configs.json')
            self._api_settings = config.get('api_settings', {})
        return self._api_settings

    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """
        特定のモデル設定を取得

        Args:
            model_name: モデル名

        Returns:
            モデル設定の辞書
        """
        models = self.model_configs

        if model_name not in models:
            raise ValueError(f"サポートされていないモデル: {model_name}")

        return models[model_name].copy()

    def get_prompt_template(self, template_name: str) -> Dict[str, Any]:
        """
        特定のプロンプトテンプレートを取得

        Args:
            template_name: テンプレート名

        Returns:
            プロンプトテンプレートの辞書
        """
        templates = self.prompt_templates

        if template_name not in templates:
            raise ValueError(f"サポートされていないプロンプトテンプレート: {template_name}")

        return templates[template_name].copy()

    def get_available_models(self) -> list[str]:
        """
        利用可能なモデルの一覧を取得

        Returns:
            モデル名のリスト
        """
        return list(self.model_configs.keys())

    def get_api_setting(self, provider: str) -> Dict[str, Any]:
        """
        特定のプロバイダのAPI設定を取得

        Args:
            provider: プロバイダ名（例: openrouter）

        Returns:
            API設定の辞書
        """
        settings = self.api_settings

        if provider not in settings:
            raise ValueError(f"サポートされていないAPIプロバイダ: {provider}")

        return settings[provider].copy()


class PromptBuilder:
    """プロンプトを構築するクラス"""

    def __init__(self, config_manager: ConfigManager):
        """
        PromptBuilderの初期化

        Args:
            config_manager: ConfigManagerインスタンス
        """
        self.config_manager = config_manager

    def build_prompt(self, template_name: str, transcript_data: str,
                    video_description: str = "") -> str:
        """
        プロンプトを構築

        Args:
            template_name: プロンプトテンプレート名
            transcript_data: 文字起こしデータ
            video_description: 動画概要

        Returns:
            構築されたプロンプト
        """
        template = self.config_manager.get_prompt_template(template_name)

        # 動画概要欄セクションの構築
        description_part = ""
        if video_description and len(video_description.strip()) > 0:
            description_text = video_description.strip()
            if len(description_text) > 1000:
                description_text = description_text[:1000] + "..."
            description_part = f"# === 動画概要欄 ===\n{description_text}\n\n"

        # プロンプトパーツの構築
        prompt_parts = [
            "# === システム指示 ===",
            template["system_message"],
            "",
            "# === トーン＆マナー ==="
        ]

        # トーン＆マナーの追加
        prompt_parts.extend(template["tone_instructions"])
        prompt_parts.extend([
            "",
            "# === 入力データ ==="
        ])

        # 動画概要の追加（存在する場合）
        if description_part:
            prompt_parts.append(description_part)

        # 文字起こしデータと出力指示の追加
        prompt_parts.extend([
            "# === 生の文字起こしデータ ===",
            "{transcript_data}",
            "// ここに文字起こしデータを貼り付ける",
            "",
            "---",
            "",
            "# === 出力指示 ==="
        ])

        prompt_parts.extend(template["output_instructions"])
        prompt_parts.append("")  # 最後の空行

        prompt = "\n".join(prompt_parts)

        # プレースホルダーの置換
        return prompt.replace("{transcript_data}", transcript_data)