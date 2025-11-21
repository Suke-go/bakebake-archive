# PLATEAU Streaming (local)

ローカルで PLATEAU の 3D Tiles を配信する最小サーバです。Range リクエストと CORS をサポートします。

## ディレクトリ構成
```
plateau-streaming/
  data/
    nagoya/
      higashi-ku/
        tileset.json
        data/...
      nishi-ku/
      nakamura-ku/
      naka-ku/
      nakagawa-ku/
      minato-ku/
    tokyo/ ...         # ← 必要に応じて追加
  server.mjs           # Node 18+ の静的配信サーバ
  package.json
  docker-compose.yml   # （任意）Nginx で配信
  nginx.conf           # （任意）Nginx 設定
```

## 使い方（Node）
1. `plateau-streaming/data/` 配下に都市名（例: `nagoya`）のディレクトリを作り、区・エリア単位で 3D Tiles を配置します。
   - 例: `plateau-streaming/data/nagoya/naka-ku/tileset.json`
   - 各区の zip を解凍し、`tileset.json` と `data/` ディレクトリをそのまま置けばOKです。
2. 実行:
   ```powershell
   cd plateau-streaming
   node server.mjs
   # 例: node server.mjs --port 8080 --dir ./data
   # もしくは環境変数: PORT=8080 DATA_DIR=./data node server.mjs
   ```
3. フロントの `.env` に URL を設定:
   - 例: `VITE_PLATEAU_3DTILES_URLS=http://localhost:8080/nagoya/naka-ku/tileset.json`
   - 複数区を読み込みたい場合はカンマ区切りで列挙します。

## 常駐運用（PM2 例）
開発マシンでタイル配信を常駐させたい場合は、`pm2.config.cjs` を利用すると簡単にバックグラウンド化できます。

```powershell
cd plateau-streaming
npx pm2 start pm2.config.cjs   # 初回起動
npx pm2 save                   # 再起動後も復元する場合
# 状態確認
npx pm2 ls
# 停止
npx pm2 stop plateau-streaming
```

環境変数（ポートやデータディレクトリ）を変更したいときは以下のいずれかを利用してください。

- `npx pm2 start pm2.config.cjs --env PORT=19090 --env DATA_DIR=C:/tiles`
- もしくは `pm2.config.cjs` の `env` セクションを直接編集

`pm2 resurrect` / `pm2 save` を組み合わせれば OS 再起動後も自動で復旧します。

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
