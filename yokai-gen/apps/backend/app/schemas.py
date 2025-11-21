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

