---
title: "How a Meta PM ships products without ever writing code | Zevi Arnovitz"
video_id: "1em64iUFt3U"
channel: "Lenny's Podcast"
published_at: "2026-01-18"
youtube_url: "https://www.youtube.com/watch?v=1em64iUFt3U"
thumbnail: "https://i.ytimg.com/vi/1em64iUFt3U/hqdefault.jpg"
summarized_at: "2026-01-24T21:41:10.773908"
model: "repaired"
---

## 技術背景ゼロのPMがAIでプロダクトを開発する完全ワークフロー

**Zevi Arnovitz**は技術背景を持たない**Meta**のプロダクトマネージャーだが、**Cursor**と**Claude Code**、**Gemini**などのAIツールを活用して、本格的なプロダクトを構築・リリースしている。彼が開発した**StudyMate**（学習資料からインタラクティブなテストを作成するプラットフォーム）や**Dibur2text**（音声認識アプリ）は、実際に収益を生み出している。

### AI活用ワークフローの全体像

Zeviのワークフローは**7つの段階**で構成されている。まず`/create_issue`コマンドで**Linear**に課題を登録し、`/exploration phase`でAIと対話しながら要件を明確化する。次に`/create plan`で実装計画をマークダウンファイルとして作成し、`/execute plan`で**Cursor Composer**を使用してコードを生成する。実装後は`/review`で自己レビューを行い、`/peer review`で異なるAIモデル同士が互いのコードをレビューさせる。最後に`/update documentation`でドキュメントを更新し、次回の開発に備える。

このワークフローの最大の特徴は、各AIモデルの特性に合わせて役割を割り当てている点だ。**Claude**は計画やアーキテクチャ、**Gemini**はUIデザイン、**Composer**は高速なコード生成に適している。Zeviはこれらを組み合わせることで、技術知識がなくても複雑なプロダクトを開発できる。

### 複数AIモデルによるピアレビュー手法

Zeviが開発した**ピアレビュー手法**は、異なるAIモデルが互いのコードをレビューし合うという革新的なアプローチだ。具体的には、**Claude Code**、**Codex**（ChatGPTのコードレビュー機能）、**Cursor Composer**の3つのモデルで同じコードをレビューさせる。それぞれのモデルが異なる視点で問題を発見するため、単一モデルでのレビューよりも多くのバグを検出できる。

各モデルには「人間のような性格」があるとZeviは説明する。**Claude**はコミュニケーション能力が高く意見を言う完璧なCTO、**Codex**は暗い部屋にこもって難解なバグを解決する優秀なコーダー、**Gemini**はアーティスティックでデザインに優れるが、作業プロセスが不安定な科学者、という具合だ。この「ピアレビュー」コマンドを使うことで、AI同士が議論し合い、最終的に最適な解決策に到達する。

### 学習と成長のためのAI活用法

ZeviはAIを単なるツールとしてではなく、**学習パートナー**として活用している。`/learning opportunity`コマンドは、理解できない技術概念を80/20ルールで説明してもらうために設計されている。これにより、技術背景のないPMでもコードベースの理解を深めることができる。

また、AIがミスをした際には、その原因を分析し、プロンプトやドキュメントを更新する**ポストモーテム**を徹底している。Zeviは「AIがミスをしたら、なぜミスをしたのかを問い、ツールやドキュメントを更新して、同じミスが二度と起きないようにする」と説明する。この継続的な改善プロセスが、AIの品質向上につながる。

### 企業でのAI導入とPMの将来

大企業でのAI導入について、Zeviは「コードベースをAIネイティブにすることが重要」と説く。技術者による適切なセットアップがあれば、PMでもUIプロジェクトなどの限定された範囲で機能を開発し、エンジニアに最終調整を依頼することは可能だ。

Zeviは「タイトルと責任が崩壊し、誰もがビルダーになる時代が来る」と予測している。技術知識がないPMでも、AIを活用することで、従来はエンジニアに依存していた作業を自ら行えるようになる。ただし、現時点ではPMが単独で複雑な機能を開発するのはリスクが高いため、エンジニアとの協働モデルが推奨される。

### AI面接準備の実践例

Zeviは**Meta**のPM面接準備にもAIを活用した。**Claude**を使ってプロジェクトを作成し、**Ben Erez**のフレームワークや**Louis Lynn**の質問バンクを取り込んだ。面接の模擬練習を行い、フィードバックをもらうことで、効率的に準備を進めた。

特に効果的だったのは、AIに「候補者」を演じさせ、完璧な回答を生成してもらうことだ。これにより、理想的な回答の構造を学ぶことができた。また、実際の人間による模擬面接も重要で、AIはあくまで補完的な役割を果たすに過ぎない。

---

## 記事のポイント

* **Cursor**と**Claude Code**を活用した7段階のAI開発ワークフロー
* 複数AIモデルによるピアレビュー手法でコード品質を担保
* **Linear**連携による課題管理と計画立案の自動化
* AIを学習パートナーとして活用し、技術知識を習得
* AIによる面接準備でPM採用試験に合格

---

## メタデータ
```
企業・組織: Meta, Wix, Anthropic, Google, StackBlitz, Linear, 10Web, DX, Framer, Replit, Base44, Bolt, Lovable
人物: Zevi Arnovitz, Lenny Rachitsky, Tal Raviv, Ben Erez, Louis Lynn, Riley Brown, Greg Isenberg, Maor Shlomo, Eric Simons, Anton Osika, Michael Truell, Nan Yu, Amjad Masad, Noam Segal
キーワード: AI開発, Cursor, Claude Code, ピアレビュー, プロダクトマネージャー, ノーコード, ワークフロー自動化, AI面接準備, StudyMate, Dibur2text
ワンライナー: 技術背景ゼロのPMがAIでプロダクトを開発する完全ワークフロー
```