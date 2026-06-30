"""Risk dashboard endpoints — reads live guardrail state off the Supervisor agent."""
from __future__ import annotations

from fastapi import APIRouter

from backend.routers.trade import loop_engine
from backend.agents import agents as agent_module
from backend.core.state import store

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/status")
async def status():
    sup = loop_engine.supervisor
    equity_curve = sup.equity_curve
    peak = max(equity_curve)
    trough = equity_curve[-1]
    drawdown_pct = ((peak - trough) / peak * 100) if peak > 0 else 0.0
    return {
        "kill_switch_active": sup.killed,
        "equity": equity_curve[-1],
        "equity_curve": equity_curve[-200:],
        "drawdown_pct": drawdown_pct,
        "guardrails": {
            "max_drawdown_pct": agent_module.MAX_DRAWDOWN,
            "vol_kill_threshold": agent_module.VOL_KILL,
            "min_confidence": agent_module.MIN_CONFIDENCE,
            "max_risk_score": agent_module.MAX_RISK_SCORE,
            "kelly_cap": agent_module.KELLY_CAP,
        },
    }


@router.post("/kill-switch")
async def kill_switch(activate: bool = True):
    loop_engine.supervisor.kill_switch(activate)
    await store.publish({"type": "kill_switch", "payload": {"active": activate}})
    return {"kill_switch_active": activate}
