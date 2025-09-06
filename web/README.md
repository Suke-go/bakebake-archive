# Toranomon Cesium Frontend (Vite + TypeScript)

最小構成の CesiumJS フロントエンドです。虎ノ門を中心とした半径 10 km を初期表示し、以下の優先順位で 3D タイルを読み込みます。

1. PLATEAU 3D Tiles（`.env` の `VITE_PLATEAU_3DTILES_URL` または `VITE_PLATEAU_3DTILES_URLS`）
2. Google Photorealistic 3D Tiles（`VITE_GOOGLE_MAPS_API_KEY`）
3. Cesium OSM Buildings（`VITE_CESIUM_ION_ACCESS_TOKEN`）

## Requirements
- Node.js 18+
- （任意）Cesium ion アクセストークン
- （任意）Google Maps Platform API キー（Map Tiles API を有効化）
- （任意）PLATEAU 3D Tiles の tileset.json へのURL（CORS許可が必要）

## Setup
```
cd web
npm install
cp .env.example .env
# 必要に応じて .env を編集
npm run dev
```

## .env keys
- `VITE_PLATEAU_3DTILES_URL`: PLATEAU の 3D Tiles `tileset.json` への URL。
  - 例: `https://<host>/plateau/tokyo_minato/tileset.json`
  - 注意: 公開サーバを利用する場合は CORS 設定が必要です。
- `VITE_PLATEAU_3DTILES_URLS`: 複数の `tileset.json` をカンマ/改行区切りで指定可能。
  - 例: `/plateau/minato/tileset.json, /plateau/chuo/tileset.json`
- `VITE_GOOGLE_MAPS_API_KEY`: Google Photorealistic 3D Tiles を使うための API キー。
  - Google Cloud で Map Tiles API を有効化してください。
- `VITE_CESIUM_ION_ACCESS_TOKEN`: OSM Buildings や World Terrain を使うためのトークン。

## What’s inside
- `index.html`: `#cesiumContainer` を全画面表示
- `src/main.ts`: ビューア作成、虎ノ門中心 (35.6664, 139.7499)、半径10km矩形へ初期移動
  - PLATEAU / Google Photorealistic / OSM Buildings を順に試行
- `vite.config.ts`: `vite-plugin-cesium` 設定

## Notes on PLATEAU
- PLATEAU（国土交通省）配布の 3D 都市モデルは、自治体単位で CityGML/3D Tiles が公開されています。
- 単一の全国共通タイルエンドポイントはなく、配布・ホスティング主体により URL や CORS 設定が異なります。
- 既存の公開タイルを参照する場合は、`tileset.json` 直リンクと CORS 許可が前提です。難しい場合はローカル or 自前ホスティングをご検討ください（静的ホスティングで `tileset.json` とバイナリ一式を配置）。
- この雛形は `VITE_PLATEAU_3DTILES_URL` もしくは `VITE_PLATEAU_3DTILES_URLS` を指定すれば自動的に読み込みます。

### ローカルにホストする方法（推奨）
1. PLATEAUの3D Tiles（zip）を入手し解凍。
2-a. 簡易: `web/public/plateau/<area>/` に配置 → `.env` に `/plateau/<area>/tileset.json`
2-b. 本番想定: `plateau-streaming/` のサーバを使い `http://localhost:8080/<area>/tileset.json`
3. `.env` に上記URLを設定。
4. `npm run dev` で確認。

## Camera preset
- 中心: 虎ノ門付近 (lat: 35.6664, lon: 139.7499)
- 初期ビュー: 半径 10,000m をおおよそカバーする矩形

## Build
```
npm run build
npm run preview
```

## Next steps
- ピン表示（GeoJSON 入力）と画像モーダル
- ズームに応じたクラスタリング
- 検索・フィルタ、i18n
