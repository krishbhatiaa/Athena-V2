"""
Controls the synthetic high-speed simulator. A single background asyncio
task repeatedly calls engine.run_batch() (vectorized numpy — thousands of
synthetic trades evaluated per batch) and publishes aggregated throughput
stats roughly every 150ms, which is the fastest a UI can usefully render
anyway. This keeps the event loop responsive (no `time.sleep`, no blocking
calls) while genuinely processing high volume under the hood.
"""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.simulator import engine
from backend.core.state import store

router = APIRouter(prefix="/simulate", tags=["simulate"])

_task: asyncio.Task | None = None
_PUBLISH_INTERVAL = 0.15


class SimConfigRequest(BaseModel):
    symbol: str | None = None
    s0: float | None = None
    mu: float | None = None
    sigma: float | None = None
    ticks_per_batch: int | None = None
    fast_window: int | None = None
    slow_window: int | None = None
    kelly_fraction: float | None = None
    fee_bps: float | None = None


async def _run_loop():
    last_publish = 0.0
    while engine.running:
        engine.run_batch()
        now = time.time()
        if now - last_publish >= _PUBLISH_INTERVAL:
            await store.publish({"type": "sim_stats", "payload": engine.stats.as_dict()})
            last_publish = now
        await asyncio.sleep(0)  # yield to the event loop — never blocks WS / HTTP traffic


@router.post("/configure")
async def configure(cfg: SimConfigRequest):
    kwargs = {k: v for k, v in cfg.model_dump().items() if v is not None}
    was_running = engine.running
    engine.stop()
    engine.configure(**kwargs)
    if was_running:
        engine.start()
    return {"config": engine.config.__dict__}


@router.post("/start")
async def start():
    global _task
    engine.start()
    if _task is None or _task.done():
        _task = asyncio.create_task(_run_loop())
    return {"status": "started", "config": engine.config.__dict__}


@router.post("/stop")
async def stop():
    engine.stop()
    return {"status": "stopped", "stats": engine.stats.as_dict()}


@router.post("/reset")
async def reset():
    engine.stop()
    engine.reset()
    return {"status": "reset"}


@router.get("/stats")
async def stats():
    return engine.stats.as_dict()
