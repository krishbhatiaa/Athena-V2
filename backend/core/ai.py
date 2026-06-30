"""
Ollama LLM client for ATHENA.

Wraps the Ollama REST API with async httpx. Gracefully degrades when
Ollama is unreachable — every public function returns None on failure,
so callers can fall back to deterministic logic.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("athena.ai")

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "30"))


async def _post(path: str, body: dict | None = None) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as cl:
            r = await cl.post(f"{OLLAMA_BASE}{path}", json=body or {})
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        logger.debug("Ollama not reachable at %s", OLLAMA_BASE)
        return None
    except Exception as exc:
        logger.warning("Ollama request failed: %s", exc)
        return None


async def _get(path: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=5) as cl:
            r = await cl.get(f"{OLLAMA_BASE}{path}")
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        return None
    except Exception as exc:
        logger.warning("Ollama GET %s failed: %s", path, exc)
        return None


async def check() -> dict | None:
    """Returns {"status":"ok","model":...} or None if Ollama is down."""
    resp = await _get("/api/tags")
    if resp is None:
        return None
    models = [m["name"] for m in resp.get("models", [])]
    return {"status": "ok", "models": models}


async def pull(model: str = OLLAMA_MODEL) -> dict | None:
    """Pull a model. Returns once done, or None on failure."""
    return await _post("/api/pull", {"name": model, "stream": False})


async def generate(
    prompt: str,
    system: str | None = None,
    model: str = OLLAMA_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> str | None:
    """Single-turn text generation. Returns the response string or None."""
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    if system:
        body["system"] = system
    resp = await _post("/api/generate", body)
    if resp is None:
        return None
    return resp.get("response", "").strip()


async def chat(
    messages: list[dict],
    model: str = OLLAMA_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> str | None:
    """Multi-turn chat. Accepts standard message format [{"role":...,"content":...}]."""
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    resp = await _post("/api/chat", body)
    if resp is None:
        return None
    return resp.get("message", {}).get("content", "").strip()
