"""FastAPI entrypoint for the yokai generator backend."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .pipeline import pipeline_manager
from .schemas import (
    GenerationRequest,
    GenerationResponse,
    HealthResponse,
    LoraInfo,
    ModelInfo,
)
from .storage import list_base_models, list_lora_weights

LOGGER = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Yokai Diffusers Backend", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _startup() -> None:
        loop = asyncio.get_event_loop()
        LOGGER.info("warming up pipeline...")
        await loop.run_in_executor(None, pipeline_manager.ensure_pipeline)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", device=pipeline_manager.device.type)

    @app.get("/models", response_model=list[ModelInfo])
    async def models() -> list[ModelInfo]:
        return [ModelInfo(name=path.name, path=path) for path in list_base_models()]

    @app.get("/lora", response_model=list[LoraInfo])
    async def lora() -> list[LoraInfo]:
        return [LoraInfo(name=path.name, path=path) for path in list_lora_weights()]

    @app.post("/generate", response_model=GenerationResponse)
    async def generate(payload: GenerationRequest) -> GenerationResponse:
        loop = asyncio.get_event_loop()
        try:
            images = await loop.run_in_executor(None, pipeline_manager.generate, payload)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Generation failed: %s", exc)
            raise HTTPException(status_code=500, detail="generation failed") from exc
        return GenerationResponse(images=images)

    return app


app = create_app()
# the script didn't import list functions - let's continue in next call

