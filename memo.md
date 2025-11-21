Yokai data import memo
======================

- ソース: ユーザー提供の CZML 風リストを `web/public/places.json` の GeoJSON に変換（30件）。
- 追加プロパティ: `id`, `title`, `description`（HTMLタグ除去済みのテキスト）, `image_url`（未設定）, `color`（point の rgba を 16進化）, `scale`（pixelSize/10）, `era`（デフォルト `past`、`鬼太郎広場` のみ `now`）。
- フロント整合性: 既存ローダーが `properties` を読む仕様。`era` フィルタは未実装なので、絞り込みしたい場合は `setTimeMode` で `entity.show` を切り替える実装を追加してください。
- 画像URL TODO: 現状すべて空。`web/public/img/yokai/` などに以下ファイルを置き、`image_url` を埋めてください（例は推奨パス名）。

  - yokai-001 のっぺらぼう → `img/yokai/yokai-001.png`
  - yokai-002 屛風のぞき → `img/yokai/yokai-002.png`
  - yokai-003 豆腐小僧 → `img/yokai/yokai-003.png`
  - yokai-004 あかなめ → `img/yokai/yokai-004.png`
  - yokai-005 轆轤首（ろくろ首） → `img/yokai/yokai-005.png`
  - yokai-006 雪女 → `img/yokai/yokai-006.png`
  - yokai-007 鎌鼬（かまいたち） → `img/yokai/yokai-007.png`
  - yokai-008 天井なめ → `img/yokai/yokai-008.png`
  - yokai-009 高女 → `img/yokai/yokai-009.png`
  - yokai-010 雷神 → `img/yokai/yokai-010.png`
  - yokai-011 鬼太郎広場 → `img/yokai/yokai-011.png`
  - yokai-012 弁慶掘の河太郎 → `img/yokai/yokai-012.png`
  - yokai-013 お岩さん → `img/yokai/yokai-013.png`
  - yokai-014 燈無蕎麦 → `img/yokai/yokai-014.png`
  - yokai-015 鸚鵡が辻 → `img/yokai/yokai-015.png`
  - yokai-016 将軍塚 → `img/yokai/yokai-016.png`
  - yokai-017 六角堂 → `img/yokai/yokai-017.png`
  - yokai-018 釘貫地蔵 → `img/yokai/yokai-018.png`
  - yokai-019 産女 → `img/yokai/yokai-019.png`
  - yokai-020 件（くだん） → `img/yokai/yokai-020.png`
  - yokai-021 朧車 → `img/yokai/yokai-021.png`
  - yokai-022 清姫 → `img/yokai/yokai-022.png`
  - yokai-023 玉藻前 → `img/yokai/yokai-023.png`
  - yokai-024 葛の葉 → `img/yokai/yokai-024.png`
  - yokai-025 華厳宗祖師絵伝（善妙の龍） → `img/yokai/yokai-025.png`
  - yokai-026 牛牧の大蛇 → `img/yokai/yokai-026.png`
  - yokai-027 蛇塚 → `img/yokai/yokai-027.png`
  - yokai-028 草薙剣 → `img/yokai/yokai-028.png`
  - yokai-029 管狐 → `img/yokai/yokai-029.png`
  - yokai-030 本宮山の山姥 → `img/yokai/yokai-030.png`

- 補足: `description` はタグ除去されるので、リッチな説明を出したい場合は `buildDescriptionHTML` 側で HTML をそのまま使うフラグを追加するなどフロント修正が必要です。
