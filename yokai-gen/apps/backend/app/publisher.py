"""Persist generated yokai images and Cesium GeoJSON entries."""

from __future__ import annotations

import json
import logging
import re
from base64 import b64decode
from pathlib import Path
from typing import Any

from .config import Settings, get_settings
from .schemas import PlaceMetadata, PublishRequest, PublishResponse

LOGGER = logging.getLogger(__name__)

_ID_PATTERN = re.compile(r"yokai-(\d+)$", re.IGNORECASE)


def _strip_data_prefix(value: str) -> str:
    if value.startswith("data:"):
        return value.split(",", 1)[-1]
    return value


def _ensure_output_dirs(settings: Settings) -> None:
    settings.places_image_dir.mkdir(parents=True, exist_ok=True)
    settings.places_json_path.parent.mkdir(parents=True, exist_ok=True)


def _load_feature_collection(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"type": "FeatureCollection", "features": []}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("features"), list):
            return data
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Failed to read %s: %s. Re-initializing.", path, exc)
    return {"type": "FeatureCollection", "features": []}


def _pick_next_id(features: list[Any], requested: str | None) -> str:
    if requested:
        return requested
    max_num = 0
    for feat in features:
        fid = ""
        if isinstance(feat, dict):
            props = feat.get("properties") or {}
            fid = str(props.get("id") or feat.get("id") or "")
        match = _ID_PATTERN.search(fid)
        if match:
            try:
                max_num = max(max_num, int(match.group(1)))
            except ValueError:
                continue
    return f"yokai-{max_num + 1:03d}"


def _save_image_png(image_b64: str, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    raw = _strip_data_prefix(image_b64)
    data = b64decode(raw)
    dest_path.write_bytes(data)


def _replace_feature(features: list[Any], feature_id: str, new_feature: dict[str, Any]) -> list[Any]:
    out: list[Any] = []
    replaced = False
    for feat in features:
        fid = ""
        if isinstance(feat, dict):
            props = feat.get("properties") or {}
            fid = str(props.get("id") or feat.get("id") or "")
        if fid == feature_id:
            out.append(new_feature)
            replaced = True
        else:
            out.append(feat)
    if not replaced:
        out.append(new_feature)
    return out


def publish_yokai(request: PublishRequest, settings: Settings | None = None) -> PublishResponse:
    """Persist a generated yokai PNG and append it to Cesium's GeoJSON."""
    cfg = settings or get_settings()
    _ensure_output_dirs(cfg)

    fc = _load_feature_collection(cfg.places_json_path)
    features: list[Any] = fc.get("features", [])
    feature_id = _pick_next_id(features, request.metadata.id)
    file_name = f"{feature_id}.png"
    image_path = cfg.places_image_dir / file_name
    image_url = f"{cfg.places_image_url_prefix.rstrip('/')}/{file_name}"

    _save_image_png(request.image_base64, image_path)

    meta: PlaceMetadata = request.metadata
    properties: dict[str, Any] = {
        "id": feature_id,
        "title": meta.title,
        "description": meta.description or "",
        "image_url": image_url,
        "color": meta.color or "#f2c14e",
        "scale": meta.scale or 1.0,
        "era": meta.era,
        "source": meta.source or "yokai-gen",
        "origin": meta.source or "yokai-gen",
    }

    # Keep prompt context around for later debugging.
    if request.prompt:
        properties["prompt"] = request.prompt
    if request.negative_prompt:
        properties["negative_prompt"] = request.negative_prompt
    if request.seed is not None:
        properties["seed"] = request.seed
    if request.lora:
        properties["lora"] = request.lora

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [meta.longitude, meta.latitude, meta.altitude or 0],
        },
        "properties": properties,
    }

    fc["features"] = _replace_feature(features, feature_id, feature)
    with cfg.places_json_path.open("w", encoding="utf-8") as fh:
        json.dump(fc, fh, ensure_ascii=False, indent=2)

    return PublishResponse(
        id=feature_id,
        image_url=image_url,
        image_path=image_path,
        places_path=cfg.places_json_path,
        places_count=len(fc["features"]),
    )
