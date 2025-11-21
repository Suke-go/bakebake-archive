# 詳細実装仕様書: 妖怪画像セグメンテーションツール

## 1. ファイル・ディレクトリ構造仕様

### 1.1 ルートディレクトリ
`yokai-gen/Preprocessing/segmentation/`

### 1.2 必須サブディレクトリ
- `inputs/`: 処理対象の画像格納先 (ユーザーが配置)
- `outputs/`: 生成されたPNG画像の保存先
- `processed/`: 処理が完了した元画像の移動先
- `checkpoints/`: モデルの重みファイル (sam_vit_h_4b8939.pth, groundingdino_swint_ogc.pth 等)

## 2. モジュール詳細仕様

### 2.1 `file_utils.py` (ファイル管理)
- **クラス**: `ImageQueue`
  - **メンバ**:
    - `file_list`: 画像パスのリスト
  - **メソッド**:
    - `__init__(input_dir)`: ディレクトリ内の画像ファイル(.jpg, .png)を取得し、ソートしてリスト化。
    - `get_next()`: リストの先頭の画像パスを返す。
    - `mark_processed(current_path, destination_dir)`: `shutil.move` で `processed/` へ移動し、リストから削除。
    - `requeue(current_path)`: リストの先頭から削除し、末尾に追加する。

### 2.2 `segmentation_utils.py` (推論エンジン)
- **依存ライブラリ**: `groundingdino`, `segment_anything`, `opencv`, `numpy`, `torch`
- **クラス**: `GroundedSAMInferencer`
  - **メソッド**:
    - `load_model()`: モデルのロード（初回のみ実行）。
    - `predict(image, text_prompt, box_threshold, text_threshold)`:
      - Grounding DINOでBBox検出。
      - SAMでBBox内のセグメンテーションマスク生成。
      - **戻り値**: マスクリスト (numpy array), プレビュー用画像 (アノテーション付き)。
    - `apply_mask(image, mask, keep_foreground=True)`:
      - アルファチャンネルを追加し、マスク領域外(or内)を透明化。

### 2.3 `app.py` (Gradio UI)
- **レイアウト**: `gr.Blocks` を使用。
- **コンポーネント**:
  - `State`: 現在処理中のファイルパスを保持。
  - `Image`: 入力画像表示。
  - `AnnotatedImage` or `Gallery`: 検出結果の表示。
  - `Textbox`: "Detection Prompt" (デフォルト: "yokai, monster, character")
  - `CheckboxGroup`: 検出されたオブジェクトから保存対象を選択（簡易化のため、すべての検出を結合するか、個別に選ぶか要調整。今回は「最大面積のものを自動選択」または「すべて結合」をデフォルトとし、修正可能にする）。
  - `Button`: "Process (Save & Next)"
  - `Button`: "Skip (Re-queue)"
- **イベントハンドラ**:
  - アプリ起動時: `ImageQueue` を初期化し、最初の画像をロード。
  - "Skip": `queue.requeue()` を呼び出し、次の画像をロード。
  - "Process": 画像保存処理を実行し、`queue.mark_processed()` を呼び出し、次の画像をロード。

## 3. 処理フロー詳細

### 3.1 起動シーケンス
1. `checkpoints/` 内のモデル有無確認（なければ自動ダウンロードのスクリプト案内）。
2. `GroundedSAMInferencer` インスタンス化。
3. `ImageQueue` インスタンス化 (`inputs/` スキャン)。
4. Gradio サーバー起動 (デフォルト `0.0.0.0:7860`, `share=True` 推奨)。

### 3.2 ユーザー操作ループ
1. **画像表示**: 現在のキュー先頭画像が表示される。
2. **自動推論**: デフォルトプロンプトで即座に推論が走る（オプション: ボタン押下で推論）。
3. **結果確認**:
   - 画面上に「背景が削除されたプレビュー」を表示。
   - ユーザーは満足なら「保存」をクリック。
   - うまく抜けていない場合、プロンプトを変更して「再推論」あるいは「閾値調整」。
4. **保存実行**:
   - `outputs/{original_filename}.png` (RGBA) として保存。
   - `inputs/{original_filename}` を `processed/{original_filename}` に移動。
   - UIは自動的に次の画像を読み込む。

### 3.3 後回し (Re-queue)
- 今の画像が難しい、あるいは後でまとめてやりたい場合。
- 物理的なファイル移動は行わず、メモリ上のキューリストの最後尾に回す。
- 即座に次の画像が表示される。

## 4. 依存関係 (requirements.txt)
```
gradio
opencv-python
numpy
torch
torchvision
(Grounded-Segment-Anything dependencies: diffusers, transformers, etc.)
```

