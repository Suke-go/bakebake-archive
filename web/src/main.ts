import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";

// 環境変数の取得（Vite）
const ION_TOKEN = (import.meta as any).env.VITE_CESIUM_ION_ACCESS_TOKEN as
  | string
  | undefined;
const GOOGLE_KEY = (import.meta as any).env.VITE_GOOGLE_MAPS_API_KEY as
  | string
  | undefined;
const PLATEAU_URL = (import.meta as any).env.VITE_PLATEAU_3DTILES_URL as
  | string
  | undefined;
const PLATEAU_URLS = (import.meta as any).env.VITE_PLATEAU_3DTILES_URLS as
  | string
  | undefined;
const YOKAI_GEN_URL = (import.meta as any).env
  .VITE_YOKAI_GENERATOR_URL as string | undefined;

// Pin visual defaults
const PIN_BASE_SIZE = 96; // px
const PIN_BORDER_PX = 4; // px
const PIN_SHADOW_BLUR = 12; // px
const PIN_HEIGHT_M = 25; // meters above ground
const PIN_LINE_COLOR = "#6a5acd"; // slateblue-like
const PIN_LINE_WIDTH = 2; // px

if (ION_TOKEN) {
  Cesium.Ion.defaultAccessToken = ION_TOKEN;
}

// ビューア生成（必要最小限のUI）
const viewer = new Cesium.Viewer("cesiumContainer", {
  animation: false,
  timeline: false,
  baseLayerPicker: false,
  geocoder: false,
  sceneModePicker: false,
  infoBox: false, // disable default InfoBox
  selectionIndicator: false,
  requestRenderMode: true,
  terrain: ION_TOKEN ? Cesium.Terrain.fromWorldTerrain() : (getEllipsoidTerrain() as any),
});

// デフォルト値（虎ノ門周辺）。app_config.json で上書き可能。
let center = { lon: 139.7499, lat: 35.6664 };
const HOME_ALTITUDE_M = 2500;
const DEFAULT_JAPAN_RECTANGLE = Cesium.Rectangle.fromDegrees(128, 30, 146, 46);
type TimeMode = "now" | "past";
type UiAction = "yokai" | "japan" | "home" | "nearby";
let currentTimeMode: TimeMode = "now";
let yokaiGeneratorUrl: string | undefined = YOKAI_GEN_URL;
let japanOverviewRectangle: Cesium.Rectangle = DEFAULT_JAPAN_RECTANGLE;

async function loadAppConfig() {
  try {
    const res = await fetch("/app_config.json");
    if (!res.ok) return;
    const config = await res.json();
    if (config.initialCenter) {
      center = config.initialCenter;
    }
    if (config.yokaiGeneratorUrl) {
      yokaiGeneratorUrl = config.yokaiGeneratorUrl;
    }
    if (isRectangleConfig(config.japanOverview)) {
      japanOverviewRectangle = Cesium.Rectangle.fromDegrees(
        config.japanOverview.west,
        config.japanOverview.south,
        config.japanOverview.east,
        config.japanOverview.north
      );
    }
  } catch (e) {
    console.warn("Failed to load app_config.json, using default center.", e);
  }
}

type RectangleConfig = {
  west: number;
  south: number;
  east: number;
  north: number;
};

function isRectangleConfig(value: any): value is RectangleConfig {
  if (!value || typeof value !== "object") return false;
  return ["west", "south", "east", "north"].every(
    (key) => typeof value[key] === "number"
  );
}

function rectangleFromCenter(
  lonDeg: number,
  latDeg: number,
  radiusMeters: number
) {
  const latDelta = radiusMeters / 111_320; // 約: 1度あたり111.32km
  const lonDelta =
    radiusMeters / (111_320 * Math.cos(Cesium.Math.toRadians(latDeg)));
  return Cesium.Rectangle.fromDegrees(
    lonDeg - lonDelta,
    latDeg - latDelta,
    lonDeg + lonDelta,
    latDeg + latDelta
  );
}

viewer.scene.globe.depthTestAgainstTerrain = true;
// Ensure user interactions are enabled
const ssc = viewer.scene.screenSpaceCameraController;
ssc.enableInputs = true;
ssc.enableRotate = true;
ssc.enableZoom = true;
ssc.enableTilt = true;
ssc.enableTranslate = true;
ssc.enableLook = true;
viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
// 地球全体が見える高さに初期化（原点上空 ~40,000km）
viewer.camera.setView({
  destination: Cesium.Cartesian3.fromDegrees(0, 0, 40_000_000),
});

// カメラ演出: 1) 全地球 → 2) 指定座標を真上から → 3) 指定座標中心のままチルト
async function flyToInitialPositionSequence() {
  const target = Cesium.Cartesian3.fromDegrees(center.lon, center.lat, 0);
  const bs = new Cesium.BoundingSphere(target, 150);

  // ヘルパー: フライト中だけ連続レンダリングを有効化
  function flyToBS(
    sphere: Cesium.BoundingSphere,
    offset: Cesium.HeadingPitchRange,
    durationSec = 3
  ) {
    return new Promise<void>((resolve) => {
      const prev = viewer.scene.requestRenderMode;
      viewer.scene.requestRenderMode = false;
      let done = false;
      const complete = () => {
        if (done) return;
        done = true;
        viewer.scene.requestRenderMode = prev;
        viewer.scene.requestRender();
        resolve();
      };
      const timer = setTimeout(complete, (durationSec + 1) * 1000);
      viewer.camera.flyToBoundingSphere(sphere, {
        offset,
        duration: durationSec,
        complete: () => {
          clearTimeout(timer);
          complete();
        },
      });
    });
  }

  // 2) 真上から（天頂）
  await flyToBS(
    bs,
    new Cesium.HeadingPitchRange(0, -Cesium.Math.PI_OVER_TWO, 2500),
    5.0
  );
  // 3) 中心を虎ノ門に保ったままチルト（俯角45°）
  await flyToBS(
    bs,
    new Cesium.HeadingPitchRange(0, -Cesium.Math.PI_OVER_FOUR, 2500),
    2.5
  );
}

type CameraViewState = {
  destination: Cesium.Cartesian3;
  orientation: {
    heading: number;
    pitch: number;
    roll: number;
  };
};

const TILE_WARMUP_OFFSETS = [
  { lonOffset: 0, latOffset: 0, heading: 0, pitch: -Cesium.Math.PI_OVER_FOUR },
  {
    lonOffset: 0.01,
    latOffset: 0.002,
    heading: Cesium.Math.PI_OVER_TWO,
    pitch: -Cesium.Math.PI_OVER_THREE,
  },
  {
    lonOffset: -0.012,
    latOffset: -0.003,
    heading: Cesium.Math.PI,
    pitch: -Cesium.Math.PI_OVER_SIX,
  },
  {
    lonOffset: 0.004,
    latOffset: -0.015,
    heading: Cesium.Math.PI * 1.5,
    pitch: -Cesium.Math.PI_OVER_FOUR,
  },
];

function captureCameraView(camera: Cesium.Camera): CameraViewState {
  return {
    destination: Cesium.Cartesian3.clone(camera.positionWC),
    orientation: {
      heading: camera.heading,
      pitch: camera.pitch,
      roll: camera.roll,
    },
  };
}

function getTileWarmupViews(baseCenter: { lon: number; lat: number }) {
  return TILE_WARMUP_OFFSETS.map((offset, idx) => ({
    destination: Cesium.Cartesian3.fromDegrees(
      baseCenter.lon + offset.lonOffset,
      baseCenter.lat + offset.latOffset,
      1500 + idx * 450
    ),
    orientation: {
      heading: offset.heading,
      pitch: offset.pitch,
      roll: 0,
    },
  }));
}

function waitForTilesetToSettle(
  tileset: Cesium.Cesium3DTileset,
  timeoutMs = 4500
) {
  const scene = viewer.scene;
  return new Promise<boolean>((resolve) => {
    const start = performance.now();
    const remove = scene.postRender.addEventListener(() => {
      if (tileset.isDestroyed()) {
        remove();
        resolve(false);
        return;
      }
      const stats = (tileset as any).statistics;
      if (
        stats &&
        stats.numberOfPendingRequests === 0 &&
        stats.numberOfTilesProcessing === 0
      ) {
        remove();
        resolve(true);
        return;
      }
      if (performance.now() - start > timeoutMs) {
        remove();
        resolve(false);
      }
    });
    scene.requestRender();
  });
}

async function preloadTilesetAroundCenter(
  tileset: Cesium.Cesium3DTileset,
  preloadCenter = center
) {
  try {
    const camera = viewer.scene.camera;
    const saved = captureCameraView(camera);
    const warmupViews = getTileWarmupViews(preloadCenter);
    for (const view of warmupViews) {
      camera.setView(view);
      viewer.scene.requestRender();
      await waitForTilesetToSettle(tileset, 5000);
    }
    camera.setView(saved);
    viewer.scene.requestRender();
  } catch (e) {
    console.warn("Tileset preload skipped", e);
  }
}

// イントロの全画面画像を一定時間表示してから解消
function showIntroOverlay(durationMs = 5000): Promise<void> {
  return new Promise((resolve) => {
    try {
      const overlay = document.createElement("div");
      overlay.id = "introOverlay";
      Object.assign(overlay.style, {
        position: "fixed",
        inset: "0",
        background: "#000",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: "9999",
        transition: "opacity 3s ease-in-out, filter 3s ease-in-out", // 長めのフェード
      } as CSSStyleDeclaration);

      const img = document.createElement("img");
      img.src = new URL("../img/intro.png", import.meta.url).href;
      Object.assign(img.style, {
        maxWidth: "90%",
        maxHeight: "90%",
        objectFit: "contain",
      } as CSSStyleDeclaration);
      overlay.appendChild(img);
      document.body.appendChild(overlay);

      // アニメーション演出
      setTimeout(() => {
        // 消えるときにぼかしを入れる（お化けが消える感じ）
        overlay.style.opacity = "0";
        overlay.style.filter = "blur(20px) grayscale(100%)";
      }, durationMs);

      // 完全に消えた後にDOM削除
      setTimeout(() => {
        overlay.remove();
        resolve();
      }, durationMs + 3000); // transition time(3s) + buffer
    } catch {
      resolve();
    }
  });
}

// ------------------------
// Geolocation (show my position)
// ------------------------
let myLocEntity: Cesium.Entity | null = null;
let myLocWatchId: number | null = null;
let myLocIconCache: HTMLCanvasElement | null = null;

function makeMyLocationIcon(size = 64): HTMLCanvasElement {
  const dpr = (window as any).devicePixelRatio || 1;
  const S = Math.max(24, size);
  const W = Math.round(S * dpr);
  const c = document.createElement("canvas");
  c.width = W;
  c.height = W;
  const ctx = c.getContext("2d")!;
  const r = W / 2 - Math.round(4 * dpr);
  // Shadowed blue disc
  ctx.beginPath();
  ctx.arc(W / 2, W / 2, r, 0, Math.PI * 2);
  ctx.closePath();
  ctx.shadowColor = "rgba(0,0,0,0.35)";
  ctx.shadowBlur = Math.round(10 * dpr);
  ctx.fillStyle = "#1a73e8"; // blue
  ctx.fill();
  // White border
  ctx.shadowBlur = 0;
  ctx.lineWidth = Math.max(2, Math.round(3 * dpr));
  ctx.strokeStyle = "#ffffff";
  ctx.stroke();
  // Center white dot
  ctx.beginPath();
  ctx.arc(W / 2, W / 2, Math.round(r * 0.25), 0, Math.PI * 2);
  ctx.closePath();
  ctx.fillStyle = "#ffffff";
  ctx.fill();
  return c;
}

function updateMyLocationEntity(lon: number, lat: number) {
  if (!myLocIconCache) myLocIconCache = makeMyLocationIcon(56);
  const posTop = Cesium.Cartesian3.fromDegrees(lon, lat, 12);
  const posGround = Cesium.Cartesian3.fromDegrees(lon, lat, 0);
  if (!myLocEntity) {
    myLocEntity = viewer.entities.add({
      position: posTop,
      billboard: {
        image: myLocIconCache as any,
        width: 56,
        height: 56,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        disableDepthTestDistance: Number.POSITIVE_INFINITY as any,
        scaleByDistance: new Cesium.NearFarScalar(1000, 1.0, 15000, 0.4),
      },
      polyline: {
        positions: [posGround, posTop],
        width: 2,
        material: Cesium.Color.fromCssColorString("#1a73e8").withAlpha(0.8),
        clampToGround: false as any,
      },
    });
  } else {
    (myLocEntity.position as any) = new Cesium.ConstantPositionProperty(posTop);
    if (myLocEntity.polyline) {
      myLocEntity.polyline.positions = [posGround, posTop] as any;
    }
  }
}

function startGeolocation() {
  if (!("geolocation" in navigator)) {
    // eslint-disable-next-line no-console
    console.warn("Geolocation not available");
    return;
  }
  try {
    myLocWatchId = navigator.geolocation.watchPosition(
      (p) => {
        const { longitude, latitude } = p.coords;
        updateMyLocationEntity(longitude, latitude);
      },
      (err) => {
        // eslint-disable-next-line no-console
        console.warn("Geolocation error", err);
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 }
    );
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn("Geolocation init failed", e);
  }
}

// GeoJSON loader for pins from local JSON
let placesDataSource: Cesium.GeoJsonDataSource | null = null;
let baseImageryLayer: Cesium.ImageryLayer | null = null;
let edoKmlDs: Cesium.KmlDataSource | null = null;

function escapeHtml(s: any): string {
  const t = String(s ?? "");
  return t
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function buildDescriptionHTML(props: any) {
  const title = escapeHtml(props?.title);
  const desc = escapeHtml(props?.description);
  const imgUrl = props?.image_url || props?.primary_image_url;
  const img = imgUrl ? `<img src="${imgUrl}" style="max-width:100%;max-height:240px;object-fit:contain;"/>` : "";
  return `${img}<div style="margin-top:8px"><strong>${title}</strong></div><div style="margin-top:4px">${desc}</div>`;
}

async function loadPinsOnce() {
  try {
    const res = await fetch("/places.json");
    if (!res.ok) return;
    const fc = await res.json();
    
    const ds = await Cesium.GeoJsonDataSource.load(fc, { clampToGround: true });
    // replace previous layer
    if (placesDataSource) viewer.dataSources.remove(placesDataSource, true);
    placesDataSource = ds;
    viewer.dataSources.add(ds);
    // clustering
    (ds.clustering as any).enabled = true;
    ds.clustering.pixelRange = 60;
    ds.clustering.minimumClusterSize = 3;
    // style
    const entities = ds.entities.values;
    for (const e of entities) {
      const p: any = (e as any).properties?.getValue?.(new Date()) ?? (e as any).properties;
      const primary = p?.image_url || p?.primary_image_url as string | undefined;
      const fallbackIcon = new URL("../img/BAKEBAKE_XR.png", import.meta.url).href;
      const imgUrl = primary || p?.icon_url || fallbackIcon;
      const colorCss = p?.color || "#ffffff";
      const userScale = Number(p?.scale ?? 1);

      // Make circular image via canvas
      const sizePx = Math.max(32, Math.round(PIN_BASE_SIZE * userScale));
      const circleImg = await makeCircularImage(imgUrl, sizePx, PIN_BORDER_PX, "#ffffff", PIN_SHADOW_BLUR);

      if (!e.billboard) e.billboard = new Cesium.BillboardGraphics();
      e.billboard.image = circleImg as any;
      e.billboard.width = sizePx;
      e.billboard.height = sizePx;
      e.billboard.verticalOrigin = Cesium.VerticalOrigin.BOTTOM;
      e.billboard.color = Cesium.Color.fromCssColorString(colorCss);
      e.billboard.disableDepthTestDistance = Number.POSITIVE_INFINITY as any; // draw over tiles
      // Scale with distance (shrink in the distance)
      e.billboard.scaleByDistance = new Cesium.NearFarScalar(1000, 1.0, 12000, 0.3);
      e.billboard.translucencyByDistance = new Cesium.NearFarScalar(2000, 1.0, 20000, 0.2);

      // Move billboard slightly above ground and add a leader line
      const now = new Date();
      const pos = (e.position as any)?.getValue?.(now) as Cesium.Cartesian3 | undefined;
      if (pos) {
        const carto = Cesium.Cartographic.fromCartesian(pos);
        const lon = carto.longitude;
        const lat = carto.latitude;
        // Billboard at height
        e.position = new Cesium.ConstantPositionProperty(
          Cesium.Cartesian3.fromRadians(lon, lat, PIN_HEIGHT_M)
        );
        // Vertical polyline from ground to the billboard
        e.polyline = new Cesium.PolylineGraphics({
          positions: [
            Cesium.Cartesian3.fromRadians(lon, lat, 0),
            Cesium.Cartesian3.fromRadians(lon, lat, PIN_HEIGHT_M),
          ],
          material: Cesium.Color.fromCssColorString(PIN_LINE_COLOR).withAlpha(0.7),
          width: PIN_LINE_WIDTH,
          clampToGround: false as any,
          zIndex: 0 as any,
        });
      }

      // Optional: small label above/below (disabled by default)
      if (!e.label) e.label = new Cesium.LabelGraphics();
      e.label.text = ""; // hide text to emphasize photos

      e.description = buildDescriptionHTML(p);
    }
  } catch (e) {
    console.warn("GeoJSON load/style failed", e);
  }
}

// Create a circular masked image with border and shadow using offscreen canvas
async function makeCircularImage(
  url: string,
  sizePx: number,
  borderPx = 4,
  borderColor = "#fff",
  shadowBlur = 12
): Promise<HTMLCanvasElement | string> {
  return new Promise((resolve) => {
    try {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        const dpr = (window as any).devicePixelRatio || 1;
        const S = Math.max(16, sizePx);
        const W = Math.round(S * dpr);
        const c = document.createElement("canvas");
        c.width = W;
        c.height = W;
        const ctx = c.getContext("2d");
        if (!ctx) {
          resolve(url);
          return;
        }
        const radius = W / 2 - Math.max(1, Math.round((borderPx * dpr) / 2));
        ctx.save();
        ctx.beginPath();
        ctx.arc(W / 2, W / 2, radius, 0, Math.PI * 2);
        ctx.closePath();
        ctx.clip();
        // cover fit
        const iw = img.naturalWidth || img.width;
        const ih = img.naturalHeight || img.height;
        const scale = Math.max(W / iw, W / ih);
        const dw = Math.ceil(iw * scale);
        const dh = Math.ceil(ih * scale);
        const dx = Math.floor((W - dw) / 2);
        const dy = Math.floor((W - dh) / 2);
        ctx.drawImage(img, dx, dy, dw, dh);
        ctx.restore();
        // border + subtle shadow
        ctx.save();
        ctx.beginPath();
        ctx.arc(W / 2, W / 2, radius, 0, Math.PI * 2);
        ctx.strokeStyle = borderColor;
        ctx.lineWidth = Math.max(1, Math.round(borderPx * dpr));
        ctx.shadowColor = "rgba(0,0,0,0.35)";
        ctx.shadowBlur = Math.round(shadowBlur * dpr);
        ctx.stroke();
        ctx.restore();
        resolve(c);
      };
      img.onerror = () => resolve(url);
      img.src = url;
    } catch {
      resolve(url);
    }
  });
}

// ------------------------
// Map Modes (Aerial / Edo KML overlay + Aerial)
// ------------------------
async function setAerialBaseImagery() {
  try {
    const layers = viewer.imageryLayers;
    if (baseImageryLayer) {
      try { layers.remove(baseImageryLayer, true); } catch {}
      baseImageryLayer = null;
    }
    const provider = await Cesium.createWorldImageryAsync({
      style: Cesium.IonWorldImageryStyle.AERIAL,
    });
    baseImageryLayer = layers.addImageryProvider(provider, 0);
    baseImageryLayer.alpha = 1.0;
  } catch (e) {
    console.warn('setAerialBaseImagery failed', e);
  }
}

function setKmlOpacity(ds: Cesium.KmlDataSource, alpha: number) {
  const entities = ds.entities.values;
  for (const e of entities) {
    const rect: any = (e as any).rectangle;
    const poly: any = (e as any).polygon;
    if (rect && rect.material && (rect.material as any).color !== undefined) {
      rect.material.color = Cesium.Color.WHITE.withAlpha(alpha);
    }
    if (poly && poly.material && (poly.material as any).color !== undefined) {
      poly.material.color = Cesium.Color.WHITE.withAlpha(alpha);
    }
    if ((e as any).billboard) {
      (e as any).billboard.color = Cesium.Color.WHITE.withAlpha(alpha);
    }
  }
}

async function showEdoOverlay(opacity = 0.65) {
  if (!edoKmlDs) {
    const kmlUrlCandidates = [
      new URL('../kml/edomap.kml', import.meta.url).href,
      new URL('../edomap.kml', import.meta.url).href,
      '/kml/edomap.kml',
      '/edomap.kml',
    ];
    let loaded: Cesium.KmlDataSource | null = null;
    for (const url of kmlUrlCandidates) {
      try {
        loaded = await Cesium.KmlDataSource.load(url, {
          camera: viewer.scene.camera,
          canvas: viewer.scene.canvas,
          clampToGround: true,
        });
        if (loaded) break;
      } catch (e) {
        // try next candidate
      }
    }
    if (!loaded) {
      console.warn('Edo KML not found. Place it at web/public/kml/edomap.kml');
      return;
    }
    edoKmlDs = loaded;
    viewer.dataSources.add(edoKmlDs);
  }
  edoKmlDs.show = true;
  try { setKmlOpacity(edoKmlDs, opacity); } catch {}
}

function hideEdoOverlay() {
  if (edoKmlDs) edoKmlDs.show = false;
}

// ------------------------
// Camera helpers & UI actions
// ------------------------
function cameraFlyTo(
  options: Cesium.Camera.FlightOptions & {
    destination: Cesium.Cartesian3 | Cesium.Rectangle;
  }
): Promise<void> {
  return new Promise((resolve) => {
    const prev = viewer.scene.requestRenderMode;
    viewer.scene.requestRenderMode = false;
    try {
      viewer.camera.flyTo({
        ...options,
        complete: () => {
          viewer.scene.requestRenderMode = prev;
          viewer.scene.requestRender();
          resolve();
        },
        cancel: () => {
          viewer.scene.requestRenderMode = prev;
          resolve();
        },
      });
    } catch (e) {
      viewer.scene.requestRenderMode = prev;
      console.warn("cameraFlyTo failed", e);
      resolve();
    }
  });
}

async function flyToJapanOverview() {
  await cameraFlyTo({
    destination: japanOverviewRectangle,
    duration: 3.0,
    orientation: {
      heading: viewer.camera.heading,
      pitch: -Cesium.Math.PI_OVER_THREE,
      roll: 0,
    },
  });
}

async function flyToHomePosition() {
  const destination = Cesium.Cartesian3.fromDegrees(
    center.lon,
    center.lat,
    HOME_ALTITUDE_M
  );
  await cameraFlyTo({
    destination,
    duration: 2.5,
    orientation: {
      heading: viewer.camera.heading,
      pitch: -Cesium.Math.PI_OVER_FOUR,
      roll: 0,
    },
  });
}

function getViewCenterCartographic(): Cesium.Cartographic | null {
  const scene = viewer.scene;
  const canvas = scene.canvas;
  const pickRay = viewer.camera.getPickRay(
    new Cesium.Cartesian2(canvas.clientWidth / 2, canvas.clientHeight / 2)
  );
  if (pickRay) {
    const pickPosition = scene.globe.pick(pickRay, scene);
    if (pickPosition) {
      return Cesium.Cartographic.fromCartesian(pickPosition);
    }
  }
  try {
    return Cesium.Cartographic.fromCartesian(viewer.camera.positionWC);
  } catch {
    return null;
  }
}

async function flyToNearestYokai() {
  if (!placesDataSource) {
    console.warn("placesDataSource is not ready.");
    return;
  }
  const centerCarto = getViewCenterCartographic();
  if (!centerCarto) return;
  const centerCartesian = Cesium.Cartesian3.fromRadians(
    centerCarto.longitude,
    centerCarto.latitude,
    0
  );
  const now = Cesium.JulianDate.now();
  let nearest: Cesium.Entity | null = null;
  let minDistance = Number.POSITIVE_INFINITY;
  for (const entity of placesDataSource.entities.values) {
    const pos = entity.position?.getValue(now);
    if (!pos) continue;
    const d = Cesium.Cartesian3.distance(centerCartesian, pos);
    if (d < minDistance) {
      minDistance = d;
      nearest = entity;
    }
  }
  if (!nearest) {
    alert("近くの妖怪が見つかりませんでした。");
    return;
  }
  try {
    await viewer.flyTo(nearest, {
      duration: 3.0,
      offset: new Cesium.HeadingPitchRange(0, -Cesium.Math.PI_OVER_FOUR, 800),
    });
  } catch (e) {
    console.warn("Failed to fly to nearest yokai", e);
  } finally {
    viewer.scene.requestRender();
  }
}

async function handleUiAction(action: UiAction) {
  switch (action) {
    case "yokai":
      if (yokaiGeneratorUrl) {
        window.open(yokaiGeneratorUrl, "_blank", "noopener,noreferrer");
      } else {
        alert(
          "妖怪生成モードのURLが設定されていません。.env の VITE_YOKAI_GENERATOR_URL または app_config.json の yokaiGeneratorUrl を設定してください。"
        );
      }
      break;
    case "japan":
      await flyToJapanOverview();
      break;
    case "home":
      await flyToHomePosition();
      break;
    case "nearby":
      await flyToNearestYokai();
      break;
    default:
      break;
  }
}

async function setTimeMode(mode: TimeMode) {
  if (mode === currentTimeMode && baseImageryLayer) {
    setActiveModeButton(mode);
    return;
  }
  if (mode === "now") {
    await setAerialBaseImagery();
    hideEdoOverlay();
  } else {
    await setAerialBaseImagery();
    await showEdoOverlay(0.65);
  }
  currentTimeMode = mode;
  setActiveModeButton(mode);
  viewer.scene.requestRender();
}

function setActiveModeButton(mode: TimeMode) {
  const root = document.getElementById("modeControls");
  if (!root) return;
  Array.from(root.querySelectorAll(".mode-btn[data-mode]")).forEach((el) => {
    const m = (el as HTMLElement).dataset.mode as TimeMode | undefined;
    if (m === mode) el.classList.add("active");
    else el.classList.remove("active");
  });
}

function setupModeControls() {
  const root = document.getElementById("modeControls");
  if (!root) return;
  root.addEventListener("click", (ev) => {
    const t = ev.target as HTMLElement | null;
    if (!t || !t.classList.contains("mode-btn")) return;
    const action = t.dataset.action as UiAction | undefined;
    if (action) {
      void handleUiAction(action);
      return;
    }
    const mode = t.dataset.mode as TimeMode | undefined;
    if (mode) {
      void setTimeMode(mode);
    }
  });
}

// 3Dタイルのロード（PLATEAU → Google Photorealistic → OSM Buildings の順で試行）
(async () => {
  await loadAppConfig();

  let loaded = false;

  // カメラ演出を開始（タイルのロードとは独立）
  // Start intro image for 5s, then run camera sequence (next frame)
  requestAnimationFrame(() => {
    showIntroOverlay(5000).then(async () => {
      flyToInitialPositionSequence().catch(() => {});
      // Load pins once for the initial view
      await loadPinsOnce();
      // Start GPS tracking
      startGeolocation();
      // Initialize map mode UI and set default to aerial imagery
      setupModeControls();
      await setTimeMode("now");
    });
  });

  // まず PLATEAU（複数URLがあれば順に追加）
  const plateauList: string[] = [];
  if (PLATEAU_URLS) {
    plateauList.push(
      ...PLATEAU_URLS.split(/[,\n]/)
        .map((s) => s.trim())
        .filter(Boolean)
    );
  }
  if (PLATEAU_URL) plateauList.push(PLATEAU_URL);

  if (plateauList.length > 0) {
    const warmedTilesets: Cesium.Cesium3DTileset[] = [];
    for (let i = 0; i < plateauList.length; i++) {
      const url = plateauList[i];
      const tileset = await addPlateauTiles(url);
      if (tileset) warmedTilesets.push(tileset);
    }
    if (warmedTilesets.length > 0) {
      for (const tileset of warmedTilesets) {
        await preloadTilesetAroundCenter(tileset, center);
      }
      loaded = true;
    }
  }

  if (!loaded && GOOGLE_KEY) {
    loaded = await addGooglePhotorealisticTiles(GOOGLE_KEY);
  }

  if (!loaded && ION_TOKEN) {
    loaded = await addOsmBuildings();
  }

  if (!loaded) {
    // 何もロードできなかった場合でも地形のみで動作
    // eslint-disable-next-line no-console
    console.warn(
      "No 3D Tiles loaded. Set PLATEAU URL, Google API key, or Cesium ion token."
    );
  }
})();

async function addPlateauTiles(
  url: string
): Promise<Cesium.Cesium3DTileset | null> {
  try {
    const tileset = await Cesium.Cesium3DTileset.fromUrl(url, {
      // パフォーマンス調整（一般的な推奨値）
      skipLevelOfDetail: true,
      baseScreenSpaceError: 1024,
      skipScreenSpaceErrorFactor: 16,
      skipLevels: 1,
      immediatelyLoadDesiredLevelOfDetail: false,
      cullRequestsWhileMoving: true,
      cullRequestsWhileMovingMultiplier: 60,
      dynamicScreenSpaceError: true,
    });
    tileset.maximumScreenSpaceError = 4;
    tileset.preloadWhenHidden = false;
    tileset.preloadFlightDestinations = true;
    tileset.backFaceCulling = true as any;
    tileset.enableShowOutline = false as any;
    viewer.scene.primitives.add(tileset);
    try {
      await (tileset as any).readyPromise;
    } catch {}
    // PLATEAUクレジット（CC BY 4.0）
    try {
      viewer.creditDisplay.addDefaultCredit(
        new (Cesium as any).Credit(
          "PLATEAU (MLIT) — CC BY 4.0",
          undefined,
          "https://www.mlit.go.jp/plateau/"
        )
      );
    } catch {}
    return tileset;
  } catch (e) {
    console.warn("PLATEAU 3D Tiles load failed:", e);
    return null;
  }
}

async function addGooglePhotorealisticTiles(apiKey: string): Promise<boolean> {
  try {
    // CesiumJS の Google Photorealistic 3D Tiles API
    // defaultApiKey を安全に設定（モジュール自体へ代入しない）
    const GoogleMaps = (Cesium as any).GoogleMaps;
    if (GoogleMaps && !GoogleMaps.defaultApiKey) {
      GoogleMaps.defaultApiKey = apiKey;
    }
    // APIキーを引数で渡せる実装にも対応（存在する場合）
    const createFn = (Cesium as any).createGooglePhotorealistic3DTileset;
    const tileset = await (createFn.length > 0
      ? createFn({ apiKey })
      : createFn());
    viewer.scene.primitives.add(tileset);
    try {
      await (tileset as any).readyPromise;
    } catch {}
    return true;
  } catch (e) {
    console.warn("Google Photorealistic 3D Tiles load failed:", e);
    return false;
  }
}

async function addOsmBuildings(): Promise<boolean> {
  try {
    const tileset = await Cesium.createOsmBuildingsAsync();
    viewer.scene.primitives.add(tileset);
    try {
      await (tileset as any).readyPromise;
    } catch {}
    return true;
  } catch (e) {
    console.warn("OSM Buildings load failed:", e);
    return false;
  }
}

function getEllipsoidTerrain(): any {
  const C: any = Cesium as any;
  // Newer API
  if (C.EllipsoidTerrain) {
    try {
      return new C.EllipsoidTerrain();
    } catch {}
  }
  // Legacy API
  if (C.EllipsoidTerrainProvider) {
    try {
      return new C.EllipsoidTerrainProvider();
    } catch {}
  }
  return undefined;
}
