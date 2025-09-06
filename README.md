# Bakebake XR (Cesium + PLATEAU + Supabase)

This repository contains a minimal CesiumJS frontend with optional local 3D Tiles streaming, and a Supabase (PostgreSQL + PostGIS + PostgREST) schema for pin data. It supports:

- 3D Tiles loading (PLATEAU URLs, Google Photorealistic, or OSM Buildings)
- Camera intro: Earth view → Toranomon zenith → tilt while keeping center
- Intro splash image (2s)
- GeoJSON pins from Supabase (circular photo billboards + leader lines)
- GPS “my location” marker (browser Geolocation API)
- Map mode buttons: Aerial imagery, Edo historical map overlay (KML)

> .env files are ignored by Git on purpose. See “Environment” below.

---

## Prerequisites

- Node.js 18+
- Git
- Optional: Docker (for Nginx streaming)
- Optional: Supabase project (PostgREST enabled)
- Optional: Cesium ion access token (imagery/terrain)
- Optional: Google Maps API key (Photorealistic 3D Tiles)

---

## Repository Structure

- `web/` – Vite + TypeScript Cesium app
  - `src/main.ts` – app entry (camera, tiles, pins, modes)
  - `index.html` – container + map mode buttons
  - `public/` – static assets served by Vite
    - `edomap.kml` – Edo historical map overlay (KML)
    - `plateau/...` – place local PLATEAU tiles here (optional)
- `plateau-streaming/` – minimal static server for 3D Tiles
  - `server.mjs` – Node HTTP server with CORS + Range
  - `docker-compose.yml`, `nginx.conf` – optional Nginx serving
- `supabase/schema.sql` – PostGIS schema + RLS + GeoJSON RPC

---

## Environment

Create `web/.env` from the example and fill as needed:

```
cp web/.env.example web/.env
```

- `VITE_PLATEAU_3DTILES_URL` – Single 3D Tiles `tileset.json` URL
- `VITE_PLATEAU_3DTILES_URLS` – Multiple `tileset.json` URLs (comma/newline separated)
- `VITE_GOOGLE_MAPS_API_KEY` – Optional (Photorealistic 3D Tiles)
- `VITE_CESIUM_ION_ACCESS_TOKEN` – Optional (OSM Buildings, terrain, imagery)
- `VITE_SUPABASE_URL` – Your Supabase project URL (for pins)
- `VITE_SUPABASE_ANON_KEY` – Supabase anon key (for pins)

`.env` files are git‑ignored.

---

## Run the Frontend

```
cd web
npm install
npm run dev
```

Open http://localhost:5173. You will see:

- 2s intro image (`web/img/intro.png`)
- Camera: Earth → Toranomon top-down (5s) → tilt (~2.5s)
- If Supabase is configured, circular photo pins load for the current view
- Right-side buttons for map modes

Build/preview:

```
npm run build
npm run preview
```

---

## 3D Tiles Options

1) Use public PLATEAU endpoints: set `VITE_PLATEAU_3DTILES_URL(S)` in `.env`.

2) Serve locally (recommended for stability):

- Node server
  ```
  cd plateau-streaming
  # Put tiles under plateau-streaming/data/<area>/tileset.json
  node server.mjs --port 8080 --dir ./data
  # then set VITE_PLATEAU_3DTILES_URL=http://localhost:8080/<area>/tileset.json
  ```

- Docker + Nginx
  ```
  cd plateau-streaming
  docker compose up -d
  # then VITE_PLATEAU_3DTILES_URL=http://localhost:8080/<area>/tileset.json
  ```

The servers set proper CORS/Range/Cache headers.

---

## Supabase (Pins)

1) Apply schema

- Open Supabase SQL editor and run `supabase/schema.sql`.
  - Enables PostGIS, creates `categories`, `places`, `place_media`
  - RLS (public read of `is_published=true`), indexes
  - RPC: `places_geojson(lon_min, lat_min, lon_max, lat_max, in_category_ids, in_since)` returns a GeoJSON FeatureCollection

2) Insert demo data

```
insert into public.categories(name, color) values ('Demo', '#ff3366') returning id;
-- use the returned id below
insert into public.places(title, description, geom, category_id, is_published)
values (
  'デモピン（虎ノ門ヒルズ）',
  'これはデモです。',
  ST_SetSRID(ST_MakePoint(139.7499, 35.6664), 4326),
  '<category_id>',
  true
);
-- Optional image
insert into public.place_media(place_id, kind, url, is_primary)
values ('<place_id>', 'image', 'https://example.com/demo.jpg', true);
```

3) Configure frontend

- Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `web/.env`
- Start `npm run dev` — pins load for the current viewport

Endpoint (manual test):
```
GET ${VITE_SUPABASE_URL}/rest/v1/rpc/places_geojson?lon_min=139.73&lat_min=35.65&lon_max=139.77&lat_max=35.69
Headers: apikey=<anon>, Authorization=Bearer <anon>
```

---

## Edo Historical Map Overlay (KML)

- Place your KML into `web/public/edomap.kml` (bundled path).
- The app tries these paths: `/kml/edomap.kml`, `/edomap.kml`, and the Vite bundle URLs.
- Use the right-side button “古地図 + 航空写真” to toggle overlay (default opacity ~0.65).

If your KML references external images, ensure they are reachable (CORS) or place those images under `web/public/kml/` with the same relative paths expected by the KML.

---

## Map Modes

- 航空写真: Ion World Imagery aerial
- 古地図 + 航空写真: Aerial + KML Edo map overlay on top

Cesium UI options used:
- `infoBox: false`, `selectionIndicator: false` (no default popups)

---

## GPS (My Location)

- Uses `navigator.geolocation.watchPosition` to show your current position
- Works on HTTPS origins (or `http://localhost`)
- Renders a blue circular marker ~12m above ground with a vertical leader line

---

## Notes & Tips

- 3D Tiles “stability” depends on network/server and LOD settings. Using a local server often improves responsiveness.
- Circular photo pins are generated client-side with an offscreen canvas (white border + shadow), scaled/tinted per properties in GeoJSON.
- Request render mode is temporarily disabled during camera flights for smooth animation.

---

## License

No license specified. Provide one if you plan to distribute.

