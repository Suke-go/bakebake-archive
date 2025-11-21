"""Utility to manage the Diffusers pipeline lifecycle."""

from __future__ import annotations

import io
import logging
import secrets
from base64 import b64encode
from pathlib import Path
from typing import Iterable

import torch
from diffusers import EulerAncestralDiscreteScheduler, StableDiffusionXLPipeline

from .config import Settings, get_settings
from .schemas import GenerationRequest, ImageResult

LOGGER = logging.getLogger(__name__)


def _detect_device(preference: str) -> torch.device:
    if preference == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    if preference == "mps" and torch.backends.mps.is_available():
        return torch.device("mps")
    if preference == "cpu":
        return torch.device("cpu")
    # auto fallback order
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _select_dtype(device: torch.device) -> torch.dtype:
    if device.type == "cuda":
        return torch.float16
    if device.type == "mps":
        return torch.float16
    return torch.float32


class PipelineManager:
    """Wraps Diffusers pipeline loading and generation."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.device = _detect_device(self.settings.device_preference)
        self.dtype = _select_dtype(self.device)
        self._pipeline: StableDiffusionXLPipeline | None = None
        self._current_lora: list[str] = []

    def _resolve_model_path(self) -> Path:
        if self.settings.default_model_subdir:
            return self.settings.model_dir / self.settings.default_model_subdir
        return self.settings.model_dir

    def ensure_pipeline(self) -> StableDiffusionXLPipeline:
        if self._pipeline is not None:
            return self._pipeline

        model_path = self._resolve_model_path()
        if not model_path.exists():
            raise FileNotFoundError(f"Base model directory not found: {model_path}")

        LOGGER.info("Loading pipeline from %s on %s", model_path, self.device)
        extra_kwargs = {}
        if not self.settings.allow_safety_checker:
            extra_kwargs["safety_checker"] = None

        pipe = StableDiffusionXLPipeline.from_pretrained(
            model_path,
            torch_dtype=self.dtype,
            **extra_kwargs,
        )
        pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)

        if self.device.type == "cuda":
            pipe.to(self.device)
            if self.settings.enable_xformers:
                pipe.enable_xformers_memory_efficient_attention()
        elif self.device.type == "mps":
            pipe.to("mps")
        else:
            pipe.to("cpu")

        self._pipeline = pipe
        return pipe

    def _apply_lora(self, lora_names: Iterable[str]) -> None:
        pipe = self.ensure_pipeline()
        names = list(lora_names)
        if names == self._current_lora:
            return

        if self._current_lora:
            try:
                pipe.unload_lora_weights()
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Failed to unload LoRA weights: %s", exc)

        if not names:
            self._current_lora = []
            return

        for name in names:
            lora_path = self.settings.lora_dir / name
            if not lora_path.exists():
                raise FileNotFoundError(f"LoRA weight not found: {lora_path}")
            LOGGER.info("Loading LoRA: %s", lora_path)
            pipe.load_lora_weights(lora_path)
        self._current_lora = names

    def _image_to_base64(self, image) -> str:  # type: ignore[no-untyped-def]
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return b64encode(buffer.getvalue()).decode("utf-8")

    def generate(self, request: GenerationRequest) -> list[ImageResult]:
        pipe = self.ensure_pipeline()
        self._apply_lora(request.lora)

        steps = request.steps or self.settings.inference_steps
        steps = min(steps, self.settings.max_inference_steps)
        guidance = request.guidance_scale or self.settings.guidance_scale
        width = request.width or self.settings.width
        height = request.height or self.settings.height
        batch = min(request.num_images, self.settings.max_batch_size)

        base_seed = request.seed if request.seed is not None else secrets.randbits(32)
        generator = torch.Generator(device=self.device)
        generator.manual_seed(base_seed)

        LOGGER.info(
            "Generating prompt='%s' lora=%s steps=%s guidance=%s size=%sx%s",
            request.prompt,
            request.lora,
            steps,
            guidance,
            width,
            height,
        )

        outputs = pipe(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            num_inference_steps=steps,
            width=width,
            height=height,
            guidance_scale=guidance,
            num_images_per_prompt=batch,
            generator=generator,
        ).images

        results: list[ImageResult] = []
        for idx, image in enumerate(outputs):
            results.append(
                ImageResult(
                    base64_png=self._image_to_base64(image),
                    seed=int(base_seed + idx),
                    width=width,
                    height=height,
                    lora=request.lora,
                )
            )
        return results


pipeline_manager = PipelineManager()

