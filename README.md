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
