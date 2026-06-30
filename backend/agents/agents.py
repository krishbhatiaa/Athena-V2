"""
ATHENA agents.

Five agents, each with a credibility weight, reasoning over the same
market snapshot. SupervisorAgent (Aegis Guard) has veto power and runs
last in every cycle — nothing executes without clearing its guardrails.

    PLAN -> ANALYZE -> RISK -> EXECUTE -> AUDIT -> CONTENT -> EXPLAIN
"""
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from backend.core import math_engine as me
from backend.core.ai import chat

OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() in ("1", "true", "yes")

Decision = Literal["BUY", "SELL", "HOLD"]


# --------------------------------------------------------------------------
# Guardrail thresholds — tune these per "Changes You Can Make" in the README
# --------------------------------------------------------------------------
MAX_DRAWDOWN = float(os.getenv("ATHENA_MAX_DRAWDOWN", "1.0"))      # percent
VOL_KILL = float(os.getenv("ATHENA_VOL_KILL", "0.50"))             # annualized sigma
MIN_CONFIDENCE = float(os.getenv("ATHENA_MIN_CONFIDENCE", "0.52")) # p_trade floor
MAX_RISK_SCORE = float(os.getenv("ATHENA_MAX_RISK_SCORE", "70"))   # 0-100
KELLY_CAP = float(os.getenv("ATHENA_KELLY_CAP", "0.25"))


@dataclass
class AgentMessage:
    agent: str
    credibility: float
    phase: str
    summary: str
    data: dict = field(default_factory=dict)
    ts: float = field(default_factory=time.time)


@dataclass
class MarketSnapshot:
    symbol: str
    closes: np.ndarray
    highs: np.ndarray
    lows: np.ndarray
    volumes: np.ndarray
    price: float


class TraderAgent:
    """Reads the 8 technical indicators and proposes a directional bias."""

    name = "Trader"
    credibility = 0.70

    def propose(self, snap: MarketSnapshot) -> AgentMessage:
        ind = me.all_indicators(snap.highs, snap.lows, snap.closes, snap.volumes)

        votes = 0
        reasons = []
        if ind["rsi"] < 30:
            votes += 1; reasons.append(f"RSI {ind['rsi']:.1f} oversold")
        elif ind["rsi"] > 70:
            votes -= 1; reasons.append(f"RSI {ind['rsi']:.1f} overbought")

        if ind["macd"]["histogram"] > 0:
            votes += 1; reasons.append("MACD histogram positive")
        else:
            votes -= 1; reasons.append("MACD histogram negative")

        pb = ind["bollinger"]["percent_b"]
        if pb < 0.05:
            votes += 1; reasons.append("price below lower Bollinger band")
        elif pb > 0.95:
            votes -= 1; reasons.append("price above upper Bollinger band")

        if ind["stochastic"]["k"] < 20:
            votes += 1; reasons.append("stochastic oversold")
        elif ind["stochastic"]["k"] > 80:
            votes -= 1; reasons.append("stochastic overbought")

        if ind["williams_r"] < -80:
            votes += 1
        elif ind["williams_r"] > -20:
            votes -= 1

        if ind["cci"] < -100:
            votes += 1
        elif ind["cci"] > 100:
            votes -= 1

        if snap.price < ind["vwap"]:
            votes += 0.5
        else:
            votes -= 0.5

        decision: Decision = "BUY" if votes >= 2 else "SELL" if votes <= -2 else "HOLD"
        strength = min(1.0, abs(votes) / 6)

        return AgentMessage(
            agent=self.name, credibility=self.credibility, phase="PLAN",
            summary=f"{decision} bias (score {votes:+.1f}/6): " + "; ".join(reasons[:3]),
            data={"decision": decision, "vote_score": votes, "strength": strength, "indicators": ind},
        )


class AnalystAgent:
    """Bayesian reasoning: converts the Trader's bias into p_trade, Kelly sizing, EV."""

    name = "Analyst"
    credibility = 0.82

    def __init__(self):
        self._prior: dict[str, float] = {}

    def analyze(self, snap: MarketSnapshot, trader_msg: AgentMessage) -> AgentMessage:
        decision = trader_msg.data["decision"]
        strength = trader_msg.data["strength"]
        prior = self._prior.get(snap.symbol, 0.5)

        # likelihoods derived from signal strength & trend persistence (Hurst)
        hurst = me.hurst_exponent(snap.closes)
        trend_bonus = 0.1 if hurst["regime"] == "trending" and decision != "HOLD" else 0.0

        likelihood_success = 0.5 + strength * 0.4 + trend_bonus
        likelihood_fail = 1 - likelihood_success
        p_trade = me.bayesian_update(prior, likelihood_success, likelihood_fail)
        self._prior[snap.symbol] = p_trade

        vol = me.realized_volatility(snap.closes)
        b = max(1.0, 2.0 - vol)  # crude payoff ratio: lower vol -> better risk/reward assumption
        kelly = me.kelly_criterion(p_trade, b, cap=KELLY_CAP)

        ev = p_trade * b - (1 - p_trade)

        return AgentMessage(
            agent=self.name, credibility=self.credibility, phase="ANALYZE",
            summary=f"p_trade={p_trade:.2f}, Kelly(capped)={kelly['capped_kelly']:.1%}, "
                    f"EV={ev:+.3f}, regime={hurst['regime']}",
            data={"p_trade": p_trade, "kelly": kelly, "ev": ev, "hurst": hurst,
                  "realized_vol": vol, "decision": decision},
        )


class RiskAgent:
    """Quantitative risk: VaR, CVaR, Sharpe, Sortino, composite risk score 0-100."""

    name = "RiskAgent"
    credibility = 0.88

    def assess(self, snap: MarketSnapshot, analyst_msg: AgentMessage) -> AgentMessage:
        vol = analyst_msg.data["realized_vol"]
        mu = 0.05  # conservative drift assumption for the risk-sizing simulation
        mc = me.monte_carlo_gbm(S0=snap.price, mu=mu, sigma=max(vol, 0.05), T=1 / 12,
                                 steps=21, sims=2000)

        # Composite 0-100 risk score: blends VaR, volatility, and Kelly aggressiveness
        kelly_frac = analyst_msg.data["kelly"]["capped_kelly"]
        risk_score = min(100.0, (
            mc["var_95"] * 100 * 0.4 +
            min(vol, 1.0) * 100 * 0.35 +
            kelly_frac * 100 * 0.25
        ))

        return AgentMessage(
            agent=self.name, credibility=self.credibility, phase="RISK",
            summary=f"Risk score {risk_score:.0f}/100 | VaR95={mc['var_95']:.2%} "
                    f"CVaR95={mc['cvar_95']:.2%} Sharpe={mc['sharpe']:.2f}",
            data={"risk_score": risk_score, "monte_carlo": mc, "volatility": vol},
        )


class SupervisorAgent:
    """Aegis Guard — final authority. Applies every guardrail; can override any trade."""

    name = "Supervisor"
    credibility = 0.95

    def __init__(self):
        self.killed = False
        self.equity_curve: list[float] = [100_000.0]

    def review(self, snap: MarketSnapshot, trader_msg, analyst_msg, risk_msg) -> AgentMessage:
        decision = trader_msg.data["decision"]
        p_trade = analyst_msg.data["p_trade"]
        risk_score = risk_msg.data["risk_score"]
        vol = risk_msg.data["volatility"]

        violations = []
        if self.killed:
            violations.append("KILL_SWITCH_ACTIVE")
        if vol >= VOL_KILL:
            violations.append(f"VOLATILITY_KILL (sigma={vol:.2%} >= {VOL_KILL:.0%})")
        if p_trade < MIN_CONFIDENCE and decision != "HOLD":
            violations.append(f"MIN_CONFIDENCE (p={p_trade:.2f} < {MIN_CONFIDENCE})")
        if risk_score >= MAX_RISK_SCORE:
            violations.append(f"RISK_SCORE_BREACH ({risk_score:.0f} >= {MAX_RISK_SCORE})")

        peak = max(self.equity_curve)
        trough = self.equity_curve[-1]
        drawdown_pct = ((peak - trough) / peak * 100) if peak > 0 else 0.0
        if drawdown_pct >= MAX_DRAWDOWN:
            violations.append(f"MAX_DRAWDOWN ({drawdown_pct:.2f}% >= {MAX_DRAWDOWN}%)")

        approved = len(violations) == 0 and decision != "HOLD"
        final_decision = decision if approved else "HOLD"

        verdict = "APPROVED" if approved else ("OVERRIDE" if decision != "HOLD" else "HOLD")
        summary = (f"{verdict}: {decision} -> {final_decision}"
                   + (f" | blocked by: {', '.join(violations)}" if violations else ""))

        return AgentMessage(
            agent=self.name, credibility=self.credibility, phase="AUDIT",
            summary=summary,
            data={"approved": approved, "final_decision": final_decision,
                  "violations": violations, "drawdown_pct": drawdown_pct},
        )

    def kill_switch(self, on: bool):
        self.killed = on


class ContentAgent:
    """Plain-English narrative generation. Uses Ollama when available; falls back
    to deterministic template engine when offline."""

    name = "ContentAgent"
    credibility = 0.78

    async def narrate(self, snap: MarketSnapshot, trader_msg, analyst_msg, risk_msg, supervisor_msg) -> AgentMessage:
        sym = snap.symbol
        decision = supervisor_msg.data["final_decision"]
        p = analyst_msg.data["p_trade"]
        risk_score = risk_msg.data["risk_score"]
        regime = analyst_msg.data["hurst"]["regime"].replace("_", " ")

        # Try AI narrative when Ollama is enabled
        body = None
        if OLLAMA_ENABLED:
            body = await self._ai_narrate(snap, trader_msg, analyst_msg, risk_msg, supervisor_msg)

        # Fall back to deterministic template
        if not body:
            if decision == "HOLD" and supervisor_msg.data["violations"]:
                body = (f"ATHENA evaluated {sym} and the Trader leaned {trader_msg.data['decision']}, "
                        f"but the Supervisor blocked execution: {', '.join(supervisor_msg.data['violations'])}. "
                        f"Staying flat protects capital until conditions normalize.")
            elif decision == "HOLD":
                body = (f"{sym} is in a {regime.replace(' ', '-')} regime without a strong enough edge "
                        f"(confidence {p:.0%}) to justify a position right now. ATHENA is holding.")
            else:
                body = (f"ATHENA is going {decision} on {sym}. Confidence sits at {p:.0%}, the market "
                        f"looks {regime}, and the composite risk score is {risk_score:.0f}/100 — within "
                        f"guardrails. Position sized via capped Kelly at "
                        f"{analyst_msg.data['kelly']['capped_kelly']:.1%} of paper capital.")

        return AgentMessage(
            agent=self.name, credibility=self.credibility, phase="CONTENT",
            summary=body, data={"narrative": body},
        )

    async def _ai_narrate(self, snap, trader_msg, analyst_msg, risk_msg, supervisor_msg) -> str | None:
        msgs = self._build_messages(snap, trader_msg, analyst_msg, risk_msg, supervisor_msg)
        return await chat(msgs, temperature=0.4)

    @staticmethod
    def _build_messages(snap, trader_msg, analyst_msg, risk_msg, supervisor_msg) -> list[dict]:
        return [
            {"role": "system", "content": "You are ATHENA, a quantitative trading agent. "
             "Write a concise 1-3 sentence narrative about the trade analysis just completed. "
             "Ground every statement in the actual numbers provided. Do not invent data. "
             "Be direct, factual, and professional — no disclaimers, no enthusiasm."},
            {"role": "user", "content": (
                f"SYMBOL: {snap.symbol} @ ${snap.price:.2f}\n"
                f"TRADER: decision={trader_msg.data['decision']}, vote_score={trader_msg.data['vote_score']:+.1f}/6\n"
                f"ANALYST: p_trade={analyst_msg.data['p_trade']:.2f}, "
                f"Kelly={analyst_msg.data['kelly']['capped_kelly']:.1%}, "
                f"EV={analyst_msg.data['ev']:+.3f}, regime={analyst_msg.data['hurst']['regime']}\n"
                f"RISK: score={risk_msg.data['risk_score']:.0f}/100, "
                f"VaR95={risk_msg.data['monte_carlo']['var_95']:.2%}, "
                f"Sharpe={risk_msg.data['monte_carlo']['sharpe']:.2f}\n"
                f"SUPERVISOR: final={supervisor_msg.data['final_decision']}, "
                f"approved={supervisor_msg.data['approved']}, "
                f"violations={' '.join(supervisor_msg.data['violations']) or 'none'}"
            )},
        ]


@dataclass
class TradeCycleResult:
    cycle_id: str
    symbol: str
    price: float
    final_decision: Decision
    messages: list[AgentMessage]
    explain: str


class AgenticLoop:
    """Orchestrates the full 7-phase cycle: PLAN -> ANALYZE -> RISK -> EXECUTE -> AUDIT -> CONTENT -> EXPLAIN."""

    def __init__(self):
        self.trader = TraderAgent()
        self.analyst = AnalystAgent()
        self.risk = RiskAgent()
        self.supervisor = SupervisorAgent()
        self.content = ContentAgent()

    async def run_cycle(self, snap: MarketSnapshot) -> TradeCycleResult:
        messages: list[AgentMessage] = []

        trader_msg = self.trader.propose(snap)                      # PLAN
        messages.append(trader_msg)

        analyst_msg = self.analyst.analyze(snap, trader_msg)        # ANALYZE
        messages.append(analyst_msg)

        risk_msg = self.risk.assess(snap, analyst_msg)              # RISK
        messages.append(risk_msg)

        supervisor_msg = self.supervisor.review(                    # EXECUTE + AUDIT
            snap, trader_msg, analyst_msg, risk_msg)
        messages.append(supervisor_msg)

        # EXECUTE: update paper equity curve on approved trades (toy P&L model)
        if supervisor_msg.data["approved"]:
            kelly_frac = analyst_msg.data["kelly"]["capped_kelly"]
            direction = 1 if supervisor_msg.data["final_decision"] == "BUY" else -1
            simulated_move = np.random.default_rng().normal(0, max(risk_msg.data["volatility"], 0.05) / 16)
            pnl_pct = direction * simulated_move * kelly_frac
            new_equity = self.supervisor.equity_curve[-1] * (1 + pnl_pct)
            self.supervisor.equity_curve.append(new_equity)

        content_msg = await self.content.narrate(                   # CONTENT
            snap, trader_msg, analyst_msg, risk_msg, supervisor_msg)
        messages.append(content_msg)

        explain = await self._explain(snap, trader_msg, analyst_msg, risk_msg, supervisor_msg)  # EXPLAIN
        messages.append(AgentMessage(
            agent="Explainability", credibility=0.95, phase="EXPLAIN", summary=explain,
        ))

        return TradeCycleResult(
            cycle_id=str(uuid.uuid4())[:8],
            symbol=snap.symbol,
            price=snap.price,
            final_decision=supervisor_msg.data["final_decision"],
            messages=messages,
            explain=explain,
        )

    @staticmethod
    async def _explain(snap, trader_msg, analyst_msg, risk_msg, supervisor_msg) -> str:
        if OLLAMA_ENABLED:
            ai = await chat([
                {"role": "system", "content": "You are ATHENA's explainability module. "
                 "Summarize the following trade cycle in 2-3 precise, factual sentences. "
                 "Include the symbol, the key numbers, and the final outcome."},
                {"role": "user", "content": (
                    f"SYMBOL: {snap.symbol} @ ${snap.price:.2f}\n"
                    f"TRADER: {trader_msg.data['decision']} (votes {trader_msg.data['vote_score']:+.1f}/6)\n"
                    f"ANALYST: p_trade={analyst_msg.data['p_trade']:.2f}, "
                    f"Kelly={analyst_msg.data['kelly']['capped_kelly']:.1%}\n"
                    f"RISK: score={risk_msg.data['risk_score']:.0f}/100, "
                    f"VaR95={risk_msg.data['monte_carlo']['var_95']:.2%}\n"
                    f"SUPERVISOR: final={supervisor_msg.data['final_decision']}, "
                    f"violations={' '.join(supervisor_msg.data['violations']) or 'none'}"
                )},
            ], temperature=0.3)
            if ai:
                return ai
        return (
            f"[{snap.symbol} @ {snap.price:.2f}] Trader proposed {trader_msg.data['decision']} "
            f"({trader_msg.summary}). Analyst computed p_trade={analyst_msg.data['p_trade']:.2f} via "
            f"Bayesian update with Kelly sizing {analyst_msg.data['kelly']['capped_kelly']:.1%}. "
            f"RiskAgent scored this {risk_msg.data['risk_score']:.0f}/100 "
            f"(VaR95={risk_msg.data['monte_carlo']['var_95']:.2%}). "
            f"Supervisor verdict: {supervisor_msg.summary}."
        )
