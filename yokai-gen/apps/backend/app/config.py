"""Application settings for the yokai generator backend."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration sourced from env vars / .env."""

    model_dir: Path = Path(__file__).resolve().parents[3] / "models" / "base"
    lora_dir: Path = Path(__file__).resolve().parents[3] / "models" / "lora"
    places_json_path: Path = Path(__file__).resolve().parents[3] / "web" / "public" / "places.json"
    places_image_dir: Path = Path(__file__).resolve().parents[3] / "web" / "public" / "img" / "yokai"
    places_image_url_prefix: str = "/img/yokai"
    default_model_subdir: str | None = None
    device_preference: Literal["auto", "cuda", "mps", "cpu"] = "auto"
    enable_xformers: bool = True
    guidance_scale: float = 7.5
    inference_steps: int = 30
    max_inference_steps: int = 60
    max_batch_size: int = 4
    width: int = 1024
    height: int = 1024
    allow_safety_checker: bool = False

    model_config = SettingsConfigDict(env_prefix="YOKAI_", env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()

