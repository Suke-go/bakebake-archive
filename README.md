# Bakebake XR (Cesium + PLATEAU)

このリポジトリは、CesiumJS を使用した Web XR / 3D マップアプリケーションのプロトタイプです。
PLATEAU 3D 都市モデルの表示、JSON ファイルによる位置情報ピン（GeoJSON）の管理、カメラ演出機能などを備えています。

## 主な機能

- **3D Tiles 表示**: PLATEAU（ローカル/リモート）、Google Photorealistic 3D Tiles、OSM Buildings の読み込み
- **カメラ演出**: 地球全体 → 虎ノ門（真上） → 傾斜ビューへのカメラワーク
- **マップモード切替**: 航空写真、古地図（江戸切絵図）オーバーレイ
- **ピン表示**: GeoJSON ファイル (`web/public/places.json`) から取得したデータをビルボードとして表示
- **現在地表示**: ブラウザの Geolocation API を使用した現在地トラッキング

## リポジトリ構成

プロジェクトは以下のコンポーネントで構成されています。詳細は各ディレクトリの README を参照してください。

| ディレクトリ | 説明 |
| --- | --- |
| [**web/**](./web/README.md) | Vite + TypeScript による Cesium フロントエンドアプリケーション。<br>メインのロジックはここにあります。 |
| [**plateau-streaming/**](./plateau-streaming/README.md) | PLATEAU 3D Tiles をローカル配信するための簡易サーバー。<br>Docker または Node.js で動作し、CORS や Range リクエストに対応しています。 |
| [**yokai-gen/**](./yokai-gen/README.md) | 妖怪生成向けのデータ前処理 / Diffusers バックエンド / React UI をまとめたスタック。 |

## クイックスタート

### 1. フロントエンドの起動

```bash
cd web
npm install
# .env ファイルを作成して必要なキーを設定（設定なしでも一部機能は動作します）
# 詳細は web/README.md を参照
npm run dev
```

`http://localhost:5173` にアクセスすると、アプリケーションが起動します。

### 2. (オプション) ローカルタイルサーバーの起動

PLATEAU のデータをローカルで高速に配信したい場合に使用します。

```bash
cd plateau-streaming
# data/ ディレクトリに tileset.json を含むデータを配置
node server.mjs --port 8080 --dir ./data
```

## 環境変数

`.env` ファイル（git 管理外）で設定を行います。詳細は [web/README.md](./web/README.md) を参照してください。

- `VITE_PLATEAU_3DTILES_URL`: PLATEAU タイルの URL
- `VITE_GOOGLE_MAPS_API_KEY`: Google Photorealistic 3D Tiles 用
- `VITE_CESIUM_ION_ACCESS_TOKEN`: Cesium ion 用

## ライセンス

MIT License (またはプロジェクトのライセンス方針に従ってください)

---

## 妖怪生成スタック (Diffusers)

Windows / macOS のローカル環境で Stable Diffusion (Diffusers) + FastAPI + React UI をセットアップするための導線を `yokai-gen/` 以下に追加しました。

### 1. Python/モデル環境の初期化

```bash
# macOS / WSL / Linux
./yokai-gen/scripts/setup_sd_env.sh

# Windows PowerShell
pwsh ./yokai-gen/scripts/setup_sd_env.ps1
```

- `.venv/` に Python 3.10+ 仮想環境を作成し、`apps/backend/requirements.txt` をインストールします。
- Hugging Face の `huggingface-cli` が見つかれば `models/base/` に `stabilityai/stable-diffusion-xl-base-1.0` をダウンロードします（要 `HF_TOKEN`）。

### 2. バックエンド (FastAPI + Diffusers)

```bash
# 共通
./yokai-gen/scripts/run_backend.sh

# Windows
pwsh ./yokai-gen/scripts/run_backend.ps1
```

環境変数:

- `YOKAI_MODEL_DIR` / `YOKAI_LORA_DIR` … ベースモデルと LoRA の配置先（デフォルトは `yokai-gen/models/...`）
- `YOKAI_DEVICE` … `auto|cuda|mps|cpu`

### 3. フロントエンド (Vite + React)

```bash
cd yokai-gen/apps/frontend
npm install
npm run dev
```

`http://localhost:5174` で、水木しげる調の UI を持つ妖怪生成フォーム＋ギャラリーを操作できます。

### 4. ワンコマンド起動 & テスト

```bash
# 両者を同時起動
./yokai-gen/scripts/dev_all.sh
# or
pwsh ./yokai-gen/scripts/dev_all.ps1

# バックエンドのユニットテスト
./yokai-gen/scripts/test_backend.sh
pwsh ./yokai-gen/scripts/test_backend.ps1
```

### 5. データ/LoRA

- 画像前処理・LoRA 学習用のスクリプトは `yokai-gen/Preprocessing/` を参照。
- 生成した LoRA (`.safetensors`) を `yokai-gen/models/lora/` に配置すると UI から選択できます。
- Nichibun 妖怪カードの主題・内容記述・画像を高速取得したい場合は `yokai-gen/Preprocessing/imagecrawler/nichibun_card_scraper.py` を利用できます。
  - 例:  
    `python yokai-gen/Preprocessing/imagecrawler/nichibun_card_scraper.py --input-csv data/cards_run2.csv --download-dir yokai-gen/Preprocessing/LoRA-making/data-source/picture --captions-dir yokai-gen/Preprocessing/LoRA-making/data-source/picture --max-workers 3 --sleep 0.5 --caption-trigger "yokai style"`  
    これで画像と `identifier.txt` キャプションがセットになり、そのまま `LoRA-making/dataset_prep.py` へ渡せます。
  - `--input-csv data/cards_run2.csv` のように既存 CSV から identifier 列を読み込み、`--resume` で途中再開、`--overwrite-images` で画像の再取得が可能です。`--max-workers` はリクエストの並列度（デフォルト 2）なので、`--sleep` と併用してサーバー負荷を避けてください。
