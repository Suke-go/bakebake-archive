"""Helpers for listing available base models and LoRA weights."""

from __future__ import annotations

from pathlib import Path

from .config import Settings, get_settings


def _list_files(directory: Path, suffixes: tuple[str, ...]) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        (p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in suffixes),
        key=lambda p: p.name,
    )


def list_base_models(settings: Settings | None = None) -> list[Path]:
    cfg = settings or get_settings()
    if cfg.default_model_subdir:
        target = cfg.model_dir / cfg.default_model_subdir
        return [target] if target.exists() else []
    return [cfg.model_dir] if cfg.model_dir.exists() else []


def list_lora_weights(settings: Settings | None = None) -> list[Path]:
    cfg = settings or get_settings()
    return _list_files(cfg.lora_dir, (".safetensors", ".pt"))

