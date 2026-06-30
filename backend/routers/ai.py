"""
AI / Ollama status and control router.
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter

from backend.core.ai import OLLAMA_MODEL, check, pull

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger("athena.ai.router")


@router.get("/status")
async def ai_status():
    enabled = os.getenv("OLLAMA_ENABLED", "true").lower() in ("1", "true", "yes")
    ollama = await check()
    return {
        "enabled": enabled,
        "ollama_reachable": ollama is not None,
        "model": OLLAMA_MODEL,
        "models": ollama.get("models", []) if ollama else [],
        "backend_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }


@router.post("/pull")
async def ai_pull(model: str = OLLAMA_MODEL):
    result = await pull(model)
    if result is None:
        return {"status": "error", "message": f"Could not pull {model} — Ollama unreachable"}
    return {"status": "ok", "model": model}
