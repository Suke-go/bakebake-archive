# 妖怪画像セグメンテーション 実装計画書

## 1. 概要
本プロジェクトは、約4000枚の妖怪画像のセグメンテーション（背景分離）を効率的に行うためのシステムを構築します。
クラウドGPU環境での実行を前提とし、`Grounded-Segment-Anything`を用いて自動検出を行い、GradioベースのWeb UIを通して人間が選別・修正を行うHuman-in-the-loopのワークフローを確立します。

## 2. アーキテクチャ構成

### 2.1 コア技術
- **セグメンテーションモデル**: [Grounded-Segment-Anything](https://github.com/IDEA-Research/Grounded-Segment-Anything)
  - Grounding DINO (テキストプロンプトによる検出) + SAM (Segment Anything Model)
- **UIフレームワーク**: **Gradio**
  - Pythonで完結し、クラウドGPU環境からWebブラウザへのアクセスが容易であるため採用します。
  - 既存のUIコンポーネント（画像表示、ボタン、テキスト入力）を活用します。

### 2.2 ディレクトリ構成
```
yokai-gen/Preprocessing/segmentation/
├── Grounded-Segment-Anything/  # (Submodule/Clone)
├── inputs/                     # 未処理画像 (4000枚)
├── outputs/                    # 処理済み(透過PNG)
├── processed/                  # 処理完了した元画像
└── src/
    ├── app.py                  # Gradio UIメインスクリプト
    ├── segmentation_utils.py   # モデル推論ラッパー
    └── file_utils.py           # ファイル操作・キュー管理
```

## 3. ワークフロー

1.  **初期化**: アプリケーション起動時に `inputs/` ディレクトリをスキャンし、処理キューを作成します。
2.  **推論実行**:
    - 先頭の画像を読み込みます。
    - デフォルトプロンプト（例: "character", "yokai", "monster"）でGrounded-SAMを実行します。
3.  **ユーザー確認 (UI)**:
    - 検出されたマスクをオーバーレイ表示します。
    - ユーザーは「残す対象（妖怪 or 背景）」を選択、またはプロンプトを修正して再推論します。
4.  **保存処理**:
    - ユーザーが「保存して次へ」を押下。
    - 選択されたマスク領域以外を透明化したPNGを `outputs/` に保存。
    - 元画像を `inputs/` から `processed/` へ移動（ファイル名は維持）。
5.  **スキップ/後回し**:
    - 「後回し」ボタン押下で、現在の画像をキューの最後尾に移動（物理的な移動はせず、リスト上の操作）。

## 4. 開発ステップ
1.  **環境構築**: Grounded-SAMの依存関係解決 (CUDA, PyTorch)。
2.  **バックエンド実装**: 画像読み込み、推論、マスク処理の実装。
3.  **UI実装**: Gradioを用いたインタフェース構築。
4.  **ファイル操作実装**: ファイル移動、キュー管理ロジックの実装。
5.  **テスト運用**: 少数枚での動作確認。

## 5. UIイメージ
- **左カラム**: 元画像 と セグメンテーション結果（マスク選択可能）
- **右カラム**:
  - テキストプロンプト入力 ("yokai" 等)
  - 検出信頼度閾値スライダー
  - アクションボタン:
    - [Save & Next (Yokai)]
    - [Save & Next (Background)]
    - [Re-queue (後回し)]

