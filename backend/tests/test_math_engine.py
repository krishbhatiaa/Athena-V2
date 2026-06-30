"""Sanity tests — run with: pytest backend/tests -v"""
import numpy as np
import pytest

from backend.core import math_engine as me


def _fake_series(n=120, seed=1):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0003, 0.015, n)
    closes = 100 * np.cumprod(1 + rets)
    highs = closes * (1 + np.abs(rng.normal(0, 0.005, n)))
    lows = closes * (1 - np.abs(rng.normal(0, 0.005, n)))
    volumes = rng.integers(1_000_000, 5_000_000, n).astype(float)
    return closes, highs, lows, volumes


def test_rsi_bounds():
    closes, *_ = _fake_series()
    val = me.rsi(closes)
    assert 0.0 <= val <= 100.0


def test_bollinger_band_ordering():
    closes, *_ = _fake_series()
    bb = me.bollinger_bands(closes)
    assert bb["lower"] <= bb["mid"] <= bb["upper"]


def test_macd_runs():
    closes, *_ = _fake_series()
    out = me.macd(closes)
    assert set(out) == {"macd", "signal", "histogram"}


def test_all_indicators_complete():
    closes, highs, lows, vols = _fake_series()
    ind = me.all_indicators(highs, lows, closes, vols)
    for key in ("rsi", "bollinger", "macd", "stochastic", "williams_r", "cci", "vwap", "atr"):
        assert key in ind


def test_black_scholes_call_put_parity():
    S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.2
    call = me.black_scholes(S, K, T, r, sigma, "call")["price"]
    put = me.black_scholes(S, K, T, r, sigma, "put")["price"]
    # Put-call parity: C - P = S - K*e^(-rT)
    lhs = call - put
    rhs = S - K * np.exp(-r * T)
    assert lhs == pytest.approx(rhs, abs=1e-6)


def test_black_scholes_call_positive():
    price = me.black_scholes(100, 100, 1.0, 0.05, 0.2, "call")["price"]
    assert price > 0


def test_greeks_delta_bounds():
    g_call = me.greeks(100, 100, 1.0, 0.05, 0.2, "call")
    g_put = me.greeks(100, 100, 1.0, 0.05, 0.2, "put")
    assert 0 <= g_call["delta"] <= 1
    assert -1 <= g_put["delta"] <= 0


def test_implied_volatility_recovers_input():
    S, K, T, r, sigma_true = 100, 105, 0.5, 0.045, 0.28
    price = me.black_scholes(S, K, T, r, sigma_true, "call")["price"]
    recovered = me.implied_volatility(price, S, K, T, r, "call")
    assert recovered == pytest.approx(sigma_true, abs=0.01)


def test_monte_carlo_shape():
    out = me.monte_carlo_gbm(100, 0.08, 0.25, 1.0, steps=50, sims=500, seed=42)
    assert out["expected_price"] > 0
    assert 0 <= out["p_profit"] <= 1
    assert out["var_95"] >= 0


def test_kelly_criterion_capped():
    k = me.kelly_criterion(p=0.9, b=2.0, cap=0.25)
    assert k["capped_kelly"] <= 0.25
    assert k["half_kelly"] == pytest.approx(k["full_kelly"] * 0.5)


def test_kelly_zero_edge_no_position():
    k = me.kelly_criterion(p=0.4, b=1.0)
    assert k["full_kelly"] == 0.0


def test_bayesian_update_smoothing():
    # Strong positive evidence should pull posterior up, but smoothing
    # keeps it short of certainty.
    post = me.bayesian_update(prior=0.5, likelihood_success=0.9, likelihood_fail=0.1)
    assert 0.5 < post < 1.0


def test_hurst_exponent_range():
    closes, *_ = _fake_series(n=300)
    out = me.hurst_exponent(closes)
    assert 0.0 <= out["hurst"] <= 1.5  # generous bound, real series can exceed [0,1] slightly
    assert out["regime"] in {"mean_reverting", "trending", "random_walk", "insufficient_data"}


def test_realized_volatility_nonnegative():
    closes, *_ = _fake_series()
    assert me.realized_volatility(closes) >= 0


@pytest.mark.asyncio
async def test_agentic_loop_runs_end_to_end():
    from backend.agents.agents import AgenticLoop, MarketSnapshot

    closes, highs, lows, vols = _fake_series(n=80)
    snap = MarketSnapshot(symbol="TEST", closes=closes, highs=highs, lows=lows,
                           volumes=vols, price=float(closes[-1]))
    loop = AgenticLoop()
    result = await loop.run_cycle(snap)
    assert result.final_decision in {"BUY", "SELL", "HOLD"}
    assert len(result.messages) == 6  # Trader, Analyst, Risk, Supervisor, Content, Explain
    assert result.explain


def test_simulator_batch_is_vectorized_and_fast():
    from backend.core.simulator import SimulationEngine
    import time

    eng = SimulationEngine()
    eng.config.ticks_per_batch = 5000
    t0 = time.perf_counter()
    stats = eng.run_batch()
    elapsed = time.perf_counter() - t0
    assert stats["batch_ticks"] == 5000
    assert elapsed < 1.0  # vectorized batch of 5000 ticks should be near-instant
