## LoRA Making Notes

- 画像の説明文は現在 1 つの CSV にまとまっており、各行に「ファイル名」と「画像の簡単な説明（キャプション）」を持たせる想定。
- `dataset_prep.py` に CSV 連携機能を追加し、`metadata.csv` などからキャプションを読み込んで画像と同名の `.txt` を生成する必要がある。
- CSV の構造を決めたら（例: `filename,caption`）、忘れずにスクリプトへ実装し、RunPod へ渡す前に `prepared-dataset/` を更新する。

> TODO: CSV 読み込みオプション（列名、ファイルパス）を `dataset_prep.py` に追加して運用ルールを文書化する。

