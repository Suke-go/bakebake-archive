from pathlib import Path

from apps.backend.app import storage
from apps.backend.app.config import Settings


class DummySettings(Settings):
    model_dir: Path = Path("/tmp/model")
    lora_dir: Path = Path("/tmp/lora")


def test_list_lora_weights(tmp_path):
    cfg = DummySettings(lora_dir=tmp_path)
    (tmp_path / "oni.safetensors").write_text("dummy", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("x", encoding="utf-8")

    paths = storage.list_lora_weights(cfg)
    assert len(paths) == 1
    assert paths[0].name == "oni.safetensors"

