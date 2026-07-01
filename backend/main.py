"""
ATHENA backend entrypoint.

    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations

import logging
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.state import store
from backend.routers import ai, analytics, data, risk, simulate, trade, ws

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("athena.main")

START_TIME = time.time()

app = FastAPI(
    title="ATHENA — Autonomous Financial Cognition Platform",
    description="Self-auditing, self-reflective multi-agent paper-trading "
                "decision engine. Paper trading only — no real money.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai.router)
app.include_router(data.router)
app.include_router(trade.router)
app.include_router(analytics.router)
app.include_router(risk.router)
app.include_router(simulate.router)
app.include_router(ws.router)

# Prometheus metrics at /metrics — optional dependency, degrades gracefully if absent.
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
except ImportError:
    logger.warning("prometheus-fastapi-instrumentator not installed — /metrics disabled")


@app.on_event("startup")
async def on_startup():
    await store.connect()
    logger.info("ATHENA backend up. State backend: %s", store.backend)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "uptime_sec": time.time() - START_TIME,
        "state_backend": store.backend,
        "mode": "paper_trading_only",
    }


@app.get("/")
async def root():
    return {
        "name": "ATHENA",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws/live",
        "note": "Paper trading only. No real money is ever at risk.",
    }
