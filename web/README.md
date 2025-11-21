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
# 下記の「.env keys」を参考に .env ファイルを作成
npm run dev
```

## .env keys
`.env` ファイルを `web/` ディレクトリ直下に作成し、以下の変数を設定してください。

- `VITE_PLATEAU_3DTILES_URL`: PLATEAU の 3D Tiles `tileset.json` への URL。
  - 例: `https://<host>/plateau/tokyo_minato/tileset.json`
  - 注意: 公開サーバを利用する場合は CORS 設定が必要です。
- `VITE_PLATEAU_3DTILES_URLS`: 複数の `tileset.json` をカンマ/改行区切りで指定可能。
  - 例: `/plateau/minato/tileset.json, /plateau/chuo/tileset.json`
- `VITE_GOOGLE_MAPS_API_KEY`: Google Photorealistic 3D Tiles を使うための API キー。
  - Google Cloud で Map Tiles API を有効化してください。
- `VITE_CESIUM_ION_ACCESS_TOKEN`: OSM Buildings や World Terrain を使うためのトークン。

## ピン情報の編集 (GeoJSON)
地図上に表示されるピンの情報は `public/places.json` で管理されています。
このファイルは標準的な GeoJSON フォーマットです。テキストエディタで編集することで、ピンの追加・削除・変更が可能です。

### データ構造例
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [139.7499, 35.6664]
      },
      "properties": {
        "title": "場所の名前",
        "description": "説明文",
        "image_url": "https://example.com/image.jpg",
        "color": "#ff3366",
        "scale": 1.0
      }
    }
  ]
}
```

- `coordinates`: `[経度, 緯度]` の順で記述します。
- `image_url`: ピンとして表示する画像の URL。
- `scale`: ピンの大きさの倍率（デフォルト 1.0）。

## Camera preset
- 中心: 虎ノ門付近 (lat: 35.6664, lon: 139.7499)
- 初期ビュー: 半径 10,000m をおおよそカバーする矩形

## Build
```
npm run build
npm run preview
```

## Notes on PLATEAU
- PLATEAU（国土交通省）配布の 3D 都市モデルは、自治体単位で CityGML/3D Tiles が公開されています。
- 単一の全国共通タイルエンドポイントはなく、配布・ホスティング主体により URL や CORS 設定が異なります。
- この雛形は `VITE_PLATEAU_3DTILES_URL` もしくは `VITE_PLATEAU_3DTILES_URLS` を指定すれば自動的に読み込みます。

### ローカルにホストする方法（推奨）
1. PLATEAUの3D Tiles（zip）を入手し解凍。
2-a. 簡易: `web/public/plateau/<area>/` に配置 → `.env` に `/plateau/<area>/tileset.json`
2-b. 本番想定: `plateau-streaming/` のサーバを使い `http://localhost:8080/<area>/tileset.json`
3. `.env` に上記URLを設定。
4. `npm run dev` で確認。
