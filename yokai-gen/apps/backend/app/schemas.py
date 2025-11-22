"""Pydantic models for API requests/responses."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Positive prompt")
    negative_prompt: str | None = Field(default=None, description="Negative prompt")
    guidance_scale: float | None = Field(default=None, ge=0.0, le=20.0)
    steps: int | None = Field(default=None, ge=1, le=100)
    seed: int | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, ge=256, le=1536, multiple_of=64)
    height: int | None = Field(default=None, ge=256, le=1536, multiple_of=64)
    num_images: int = Field(default=1, ge=1, le=4)
    lora: list[str] = Field(default_factory=list, description="LoRA filenames to apply")


class ImageResult(BaseModel):
    base64_png: str
    seed: int
    width: int
    height: int
    lora: list[str]


class GenerationResponse(BaseModel):
    images: list[ImageResult]


class ModelInfo(BaseModel):
    name: str
    path: Path


class LoraInfo(BaseModel):
    name: str
    path: Path


class HealthResponse(BaseModel):
    status: Literal["ok"]
    device: str


class PlaceMetadata(BaseModel):
    """Metadata for persisting a generated yokai onto the Cesium map."""

    title: str = Field(..., min_length=1, description="Display title shown in Cesium")
    description: str | None = Field(default=None, description="Long-form description / lore")
    longitude: float = Field(..., ge=-180.0, le=180.0)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    altitude: float | None = Field(default=0.0)
    color: str | None = Field(default="#f2c14e", description="CSS color for the pin")
    scale: float | None = Field(default=1.0, gt=0)
    era: Literal["now", "past"] = "now"
    id: str | None = Field(default=None, description="Optional explicit id such as yokai-031")
    source: str | None = Field(default="yokai-gen")


class PublishRequest(BaseModel):
    """Publish a generated image into the Cesium GeoJSON dataset."""

    metadata: PlaceMetadata
    image_base64: str = Field(..., description="PNG data (base64, without data URI)")
    prompt: str | None = None
    negative_prompt: str | None = None
    seed: int | None = None
    lora: list[str] = Field(default_factory=list)


class PublishResponse(BaseModel):
    id: str
    image_url: str
    image_path: Path
    places_path: Path
    places_count: int

