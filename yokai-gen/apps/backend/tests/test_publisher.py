import base64
import io
import json
from pathlib import Path

from PIL import Image

from apps.backend.app.config import Settings
from apps.backend.app.publisher import publish_yokai
from apps.backend.app.schemas import PlaceMetadata, PublishRequest


class DummySettings(Settings):
    model_dir: Path = Path("/tmp/model")
    lora_dir: Path = Path("/tmp/lora")


def _make_image_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (255, 0, 0)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def test_publish_writes_png_and_updates_geojson(tmp_path: Path) -> None:
    cfg = DummySettings(
        places_json_path=tmp_path / "places.json",
        places_image_dir=tmp_path / "img" / "yokai",
        places_image_url_prefix="/img/yokai",
    )
    payload = PublishRequest(
        metadata=PlaceMetadata(
            title="テスト妖怪",
            description="赤い妖怪のメモ",
            longitude=139.7,
            latitude=35.6,
            era="now",
        ),
        image_base64=_make_image_b64(),
        prompt="prompt text",
        negative_prompt="neg",
        seed=123,
        lora=["lora-a"],
    )

    resp = publish_yokai(payload, cfg)

    assert resp.id.startswith("yokai-")
    assert resp.image_path.exists()
    assert resp.places_path.exists()

    fc = json.loads(resp.places_path.read_text(encoding="utf-8"))
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1
    props = fc["features"][0]["properties"]
    assert props["title"] == "テスト妖怪"
    assert props["origin"] == "yokai-gen"
    assert props["prompt"] == "prompt text"
