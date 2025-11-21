## LoRA Making Notes

- 画像と説明文は現在 1 つの CSV にまとまっており、各行に「ファイル名」と「画像の簡単な説明（キャプション）」を持たせる想定。
- `dataset_prep.py` に CSV 連携機能を追加し、`metadata.csv` などからキャプションを読み込んで画像と同名の `.txt` を生成する案がある。
- CSV の構造を決めたら（例: `filename,caption`）、忘れずにスクリプトへ実装し、RunPod へ渡す前に `prepared-dataset/` を更新する。

> TODO: CSV 読み込みオプションの名前・ファイルパスを `dataset_prep.py` に追加して運用ルールを文書化する。

## RunPod での学習メモ

- `runpod/setup.sh` … H100 向けに torch 2.3.1 + cu121 / xformers 0.0.27 を固定インストール。bitsandbytes は `INSTALL_BITSANDBYTES=0` でスキップ可。
- `runpod/train.sh` … `MIXED_PRECISION=fp16` で fp16 に切り替え可。`models/base/sd_xl_base_1.0.safetensors` と `prepared-dataset/` が同梱されていれば `/workspace/models` と `/workspace/datasets/yokai/train` に自動 symlink する。
- コンテナ起動後: `bash runpod/setup.sh && bash runpod/train.sh`。`CONFIG_FILE` や `MODEL_SRC_DEFAULT`/`DATASET_SRC_DEFAULT` を環境変数で差し替えれば別ファイルを参照可能。
