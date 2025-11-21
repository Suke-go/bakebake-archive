## yokai-gen

妖怪生成スタックのルート。前処理スクリプトとローカル向け Diffusers + React アプリをまとめています。

### ディレクトリ

| パス | 説明 |
| --- | --- |
| `Preprocessing/` | 画像クローラー・セグメンテーション・LoRA 準備のユーティリティ。 |
| `apps/backend/` | FastAPI + Diffusers による推論 API。 |
| `apps/frontend/` | 妖怪特徴フォーム＋ギャラリー UI (Vite + React)。 |
| `models/base/` | Stable Diffusion 本体（Hugging Face から取得）。 |
| `models/lora/` | 生成した LoRA を配置。 |
| `scripts/` | セットアップ / 起動 / テスト補助スクリプト。 |

### セットアップ

1. 依存関係とモデルダウンロード  
   `./scripts/setup_sd_env.sh` または `pwsh ./scripts/setup_sd_env.ps1`
2. バックエンド起動  
   `./scripts/run_backend.sh`
3. フロントエンド起動  
   `cd apps/frontend && npm install && npm run dev`

`./scripts/dev_all.*` を使えばフロント + バックエンドを同時起動できます。

