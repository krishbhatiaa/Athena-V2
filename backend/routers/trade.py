"""
Trade execution: runs the full 5-agent, 7-phase loop against live (delayed,
free) market data. This is the "real money mental model, paper money
execution" path — distinct from the synthetic high-speed simulator.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from backend.agents.agents import AgenticLoop, MarketSnapshot
from backend.core.state import store
from backend.core.yf import fetch_history

router = APIRouter(prefix="/trade", tags=["trade"])

loop_engine = AgenticLoop()


async def _fetch_snapshot(symbol: str) -> MarketSnapshot:
    try:
        df = await asyncio.to_thread(fetch_history, symbol, "3mo", "1d")
    except Exception as exc:
        raise HTTPException(502, f"Could not fetch data for {symbol}: {exc}")
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    return MarketSnapshot(
        symbol=symbol.upper(),
        closes=df["Close"].to_numpy(dtype=float),
        highs=df["High"].to_numpy(dtype=float),
        lows=df["Low"].to_numpy(dtype=float),
        volumes=df["Volume"].to_numpy(dtype=float),
        price=float(df["Close"].iloc[-1]),
    )


@router.post("/execute")
async def execute(symbol: str = "AAPL"):
    snap = await _fetch_snapshot(symbol)
    result = await loop_engine.run_cycle(snap)

    record = {
        "cycle_id": result.cycle_id,
        "symbol": result.symbol,
        "price": result.price,
        "final_decision": result.final_decision,
        "explain": result.explain,
        "messages": [
            {"agent": m.agent, "credibility": m.credibility, "phase": m.phase,
             "summary": m.summary, "ts": m.ts}
            for m in result.messages
        ],
    }
    await store.push_list("trade:history", record)
    for m in result.messages:
        await store.push_list("trade:logs", {
            "agent": m.agent, "credibility": m.credibility, "phase": m.phase,
            "summary": m.summary, "ts": m.ts,
        })
    await store.publish({"type": "trade_executed", "payload": record})
    return record


@router.get("/history")
async def history(limit: int = 100):
    return await store.get_list("trade:history", limit=limit)


@router.get("/logs")
async def logs(limit: int = 300):
    return await store.get_list("trade:logs", limit=limit)


@router.post("/reset")
async def reset():
    """Safety ceremony — wipes history and resets equity curve / Bayesian priors.
    Mutates the existing AgenticLoop in place (rather than rebinding loop_engine)
    so every module holding a reference — e.g. routers/risk.py — stays in sync."""
    loop_engine.analyst._prior.clear()
    loop_engine.supervisor.killed = False
    loop_engine.supervisor.equity_curve.clear()
    loop_engine.supervisor.equity_curve.append(100_000.0)
    await store.delete_key("trade:history")
    await store.delete_key("trade:logs")
    msg = {"type": "reset", "payload": {"message": "ATHENA reset — all priors, "
                                          "equity curve, and history cleared."}}
    await store.publish(msg)
    return {"status": "reset_complete", "equity": loop_engine.supervisor.equity_curve[-1]}
