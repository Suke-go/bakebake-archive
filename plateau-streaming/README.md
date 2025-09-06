# PLATEAU Streaming (local)

ローカルで PLATEAU の 3D Tiles を配信する最小サーバです。Range リクエストと CORS をサポートします。

## ディレクトリ構成
```
plateau-streaming/
  data/                # ← ここに tileset.json とバイナリ一式を配置
  server.mjs           # Node 18+ の静的配信サーバ
  package.json
  docker-compose.yml   # （任意）Nginx で配信
  nginx.conf           # （任意）Nginx 設定
```

## 使い方（Node）
1. `plateau-streaming/data/` に PLATEAU の 3D Tiles を展開（`tileset.json` が直下 or サブディレクトリにある）
2. 実行:
   ```powershell
   cd plateau-streaming
   node server.mjs
   # 例: node server.mjs --port 8080 --dir ./data
   # もしくは環境変数: PORT=8080 DATA_DIR=./data node server.mjs
   ```
3. フロントの `.env` に URL を設定:
   - 例: `VITE_PLATEAU_3DTILES_URL=http://localhost:8080/minato/tileset.json`

## 使い方（Docker/Nginx・任意）
1. `data/` に 3D Tiles を配置
2. 実行:
   ```bash
   cd plateau-streaming
   docker compose up -d
   ```
3. アクセス: `http://localhost:8080/.../tileset.json`

## 備考（チュートリアルの要点まとめ）
以下の推奨事項に準拠しています（PLATEAU配信サービス・チュートリアルの要点）。
- 静的配信 + CORS + Range(bytes) に対応
- `GET/HEAD/OPTIONS` サポート、プリフライトOK
- ヘッダ: `Access-Control-Allow-Origin: *`, `Accept-Ranges: bytes`, `Access-Control-Expose-Headers: Content-Length, Content-Range`, `Cache-Control: public, max-age=604800, immutable, no-transform`
- 条件付きリクエスト: `ETag` / `Last-Modified` / `If-None-Match` / `If-Modified-Since`
- 事前圧縮ファイル（`*.json.gz`, `*.b3dm.gz` 等）に対して `Content-Encoding: gzip` を付与
- Nginx は `gzip_static on;` で `*.gz` を自動返却、`etag on;`、`if_modified_since exact;`
- 公開運用は S3(+CloudFront) や GCS(+Cloud CDN) などの静的配信でOK（Range 透過を確認）
