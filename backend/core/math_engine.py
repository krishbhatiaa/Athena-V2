"""
ATHENA math engine.

Every function here is a real, from-scratch numerical implementation —
no mocked numbers. Inputs are plain numpy arrays / lists so this module
has zero dependency on the web framework and can be unit tested in
isolation (see backend/tests/test_math_engine.py).
"""
from __future__ import annotations

import math
from typing import Literal

import numpy as np
from scipy.stats import norm

EPS = 1e-12


# --------------------------------------------------------------------------
# Technical indicators
# --------------------------------------------------------------------------

def rsi(closes: np.ndarray, period: int = 14) -> float:
    """Relative Strength Index, Wilder's smoothing. Returns latest value 0-100."""
    closes = np.asarray(closes, dtype=float)
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss < EPS:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def bollinger_bands(closes: np.ndarray, period: int = 20, num_std: float = 2.0) -> dict:
    closes = np.asarray(closes, dtype=float)
    if len(closes) < period:
        period = max(2, len(closes))
    window = closes[-period:]
    mid = float(np.mean(window))
    std = float(np.std(window))
    upper = mid + num_std * std
    lower = mid - num_std * std
    price = float(closes[-1])
    band_width = upper - lower
    percent_b = (price - lower) / band_width if band_width > EPS else 0.5
    return {"upper": upper, "mid": mid, "lower": lower, "percent_b": percent_b, "bandwidth": band_width}


def ema(values: np.ndarray, period: int) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    alpha = 2 / (period + 1)
    out = np.empty_like(values)
    out[0] = values[0]
    for i in range(1, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def macd(closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    closes = np.asarray(closes, dtype=float)
    if len(closes) < slow + signal:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return {"macd": float(macd_line[-1]), "signal": float(signal_line[-1]), "histogram": float(hist[-1])}


def stochastic(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14, d_period: int = 3) -> dict:
    highs, lows, closes = (np.asarray(a, dtype=float) for a in (highs, lows, closes))
    n = min(len(closes), period)
    hh = np.max(highs[-n:])
    ll = np.min(lows[-n:])
    denom = hh - ll
    k = 100 * (closes[-1] - ll) / denom if denom > EPS else 50.0
    # %D = simple moving average of last d_period %K values
    ks = []
    for i in range(d_period):
        idx = len(closes) - i
        if idx < n:
            break
        seg_h = highs[max(0, idx - n):idx]
        seg_l = lows[max(0, idx - n):idx]
        seg_c = closes[idx - 1]
        seg_hh, seg_ll = np.max(seg_h), np.min(seg_l)
        d = seg_hh - seg_ll
        ks.append(100 * (seg_c - seg_ll) / d if d > EPS else 50.0)
    d_val = float(np.mean(ks)) if ks else k
    return {"k": float(k), "d": d_val}


def williams_r(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    highs, lows, closes = (np.asarray(a, dtype=float) for a in (highs, lows, closes))
    n = min(len(closes), period)
    hh = np.max(highs[-n:])
    ll = np.min(lows[-n:])
    denom = hh - ll
    if denom < EPS:
        return -50.0
    return float(-100 * (hh - closes[-1]) / denom)


def cci(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 20) -> float:
    highs, lows, closes = (np.asarray(a, dtype=float) for a in (highs, lows, closes))
    n = min(len(closes), period)
    tp = (highs[-n:] + lows[-n:] + closes[-n:]) / 3.0
    sma = np.mean(tp)
    mean_dev = np.mean(np.abs(tp - sma))
    if mean_dev < EPS:
        return 0.0
    return float((tp[-1] - sma) / (0.015 * mean_dev))


def vwap(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> float:
    highs, lows, closes, volumes = (np.asarray(a, dtype=float) for a in (highs, lows, closes, volumes))
    typical = (highs + lows + closes) / 3.0
    vol_sum = np.sum(volumes)
    if vol_sum < EPS:
        return float(closes[-1])
    return float(np.sum(typical * volumes) / vol_sum)


def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    highs, lows, closes = (np.asarray(a, dtype=float) for a in (highs, lows, closes))
    if len(closes) < 2:
        return float(highs[-1] - lows[-1]) if len(highs) else 0.0
    prev_close = closes[:-1]
    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - prev_close)
    tr3 = np.abs(lows[1:] - prev_close)
    tr = np.maximum.reduce([tr1, tr2, tr3])
    n = min(len(tr), period)
    return float(np.mean(tr[-n:]))


def all_indicators(highs, lows, closes, volumes) -> dict:
    """Compute all 8 indicators in one pass for the Trader agent."""
    return {
        "rsi": rsi(closes),
        "bollinger": bollinger_bands(closes),
        "macd": macd(closes),
        "stochastic": stochastic(highs, lows, closes),
        "williams_r": williams_r(highs, lows, closes),
        "cci": cci(highs, lows, closes),
        "vwap": vwap(highs, lows, closes, volumes),
        "atr": atr(highs, lows, closes),
    }


# --------------------------------------------------------------------------
# Black-Scholes option pricing & Greeks
# --------------------------------------------------------------------------

OptionType = Literal["call", "put"]


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    T = max(T, 1e-6)
    sigma = max(sigma, 1e-6)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def black_scholes(S: float, K: float, T: float, r: float, sigma: float, option_type: OptionType = "call") -> dict:
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    if option_type == "call":
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return {"price": float(price), "d1": float(d1), "d2": float(d2)}


def greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: OptionType = "call") -> dict:
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    T = max(T, 1e-6)
    sigma = max(sigma, 1e-6)
    pdf_d1 = norm.pdf(d1)
    if option_type == "call":
        delta = norm.cdf(d1)
        theta = (-(S * pdf_d1 * sigma) / (2 * math.sqrt(T))
                 - r * K * math.exp(-r * T) * norm.cdf(d2))
        rho = K * T * math.exp(-r * T) * norm.cdf(d2)
    else:
        delta = norm.cdf(d1) - 1
        theta = (-(S * pdf_d1 * sigma) / (2 * math.sqrt(T))
                 + r * K * math.exp(-r * T) * norm.cdf(-d2))
        rho = -K * T * math.exp(-r * T) * norm.cdf(-d2)
    gamma = pdf_d1 / (S * sigma * math.sqrt(T))
    vega = S * pdf_d1 * math.sqrt(T)
    return {
        "delta": float(delta),
        "gamma": float(gamma),
        "theta": float(theta / 365),  # per-day theta
        "vega": float(vega / 100),    # per 1% vol move
        "rho": float(rho / 100),      # per 1% rate move
    }


def implied_volatility(market_price: float, S: float, K: float, T: float, r: float,
                        option_type: OptionType = "call", tol: float = 1e-6, max_iter: int = 100) -> float:
    """Newton-Raphson with bisection fallback for robustness."""
    sigma = 0.3
    for _ in range(max_iter):
        price = black_scholes(S, K, T, r, sigma, option_type)["price"]
        vega = greeks(S, K, T, r, sigma, option_type)["vega"] * 100  # undo the /100 scaling
        diff = market_price - price
        if abs(diff) < tol:
            return float(sigma)
        if vega < EPS:
            break
        sigma += diff / vega
        if sigma <= 0:
            sigma = 0.01
    # Bisection fallback
    lo, hi = 1e-4, 5.0
    for _ in range(200):
        mid = (lo + hi) / 2
        price = black_scholes(S, K, T, r, mid, option_type)["price"]
        if abs(price - market_price) < tol:
            return float(mid)
        if price > market_price:
            hi = mid
        else:
            lo = mid
    return float((lo + hi) / 2)


def greeks_surface(S: float, r: float, sigma: float, option_type: OptionType,
                    strikes: np.ndarray, expiries: np.ndarray) -> list[dict]:
    out = []
    for T in expiries:
        for K in strikes:
            g = greeks(S, float(K), float(T), r, sigma, option_type)
            out.append({"strike": float(K), "expiry": float(T), **g})
    return out


# --------------------------------------------------------------------------
# Monte Carlo — Geometric Brownian Motion
# --------------------------------------------------------------------------

def monte_carlo_gbm(S0: float, mu: float, sigma: float, T: float,
                     steps: int = 252, sims: int = 5000, rf: float = 0.0,
                     seed: int | None = None) -> dict:
    """
    dS = S(mu*dt + sigma*dW)
    Returns terminal price distribution stats plus VaR/CVaR/Sharpe/Sortino.
    """
    rng = np.random.default_rng(seed)
    dt = T / steps
    z = rng.standard_normal((sims, steps))
    log_returns = (mu - 0.5 * sigma ** 2) * dt + sigma * math.sqrt(dt) * z
    paths = S0 * np.exp(np.cumsum(log_returns, axis=1))
    paths = np.hstack([np.full((sims, 1), S0), paths])
    terminal = paths[:, -1]
    rets = terminal / S0 - 1

    var_95 = float(-np.percentile(rets, 5))
    tail = rets[rets <= np.percentile(rets, 5)]
    cvar_95 = float(-np.mean(tail)) if len(tail) else var_95

    mean_ret = float(np.mean(rets))
    std_ret = float(np.std(rets))
    sharpe = (mean_ret - rf) / std_ret if std_ret > EPS else 0.0

    downside = rets[rets < rf]
    downside_std = float(np.std(downside)) if len(downside) else EPS
    sortino = (mean_ret - rf) / downside_std if downside_std > EPS else 0.0

    p_profit = float(np.mean(rets > 0))
    percentiles = {p: float(np.percentile(terminal, p)) for p in (5, 25, 50, 75, 95)}

    return {
        "expected_price": float(np.mean(terminal)),
        "std_dev": float(np.std(terminal)),
        "var_95": var_95,
        "cvar_95": cvar_95,
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "p_profit": p_profit,
        "percentiles": percentiles,
        "sample_paths": paths[:: max(1, sims // 30), :: max(1, steps // 100)].tolist(),
    }


def portfolio_monte_carlo(weights: np.ndarray, mus: np.ndarray, sigmas: np.ndarray,
                           corr: np.ndarray, S0_total: float, T: float,
                           steps: int = 252, sims: int = 3000, seed: int | None = None) -> dict:
    """Correlated multi-asset GBM portfolio simulation via Cholesky decomposition."""
    rng = np.random.default_rng(seed)
    n_assets = len(weights)
    dt = T / steps
    L = np.linalg.cholesky(corr + np.eye(n_assets) * 1e-10)

    portfolio_paths = np.zeros((sims, steps + 1))
    portfolio_paths[:, 0] = S0_total

    asset_vals = np.tile(weights * S0_total, (sims, 1))
    for t in range(1, steps + 1):
        z = rng.standard_normal((sims, n_assets)) @ L.T
        growth = np.exp((mus - 0.5 * sigmas ** 2) * dt + sigmas * math.sqrt(dt) * z)
        asset_vals = asset_vals * growth
        portfolio_paths[:, t] = np.sum(asset_vals, axis=1)

    terminal = portfolio_paths[:, -1]
    rets = terminal / S0_total - 1
    var_95 = float(-np.percentile(rets, 5))
    tail = rets[rets <= np.percentile(rets, 5)]
    cvar_95 = float(-np.mean(tail)) if len(tail) else var_95
    return {
        "expected_value": float(np.mean(terminal)),
        "std_dev": float(np.std(terminal)),
        "var_95": var_95,
        "cvar_95": cvar_95,
        "p_profit": float(np.mean(rets > 0)),
    }


# --------------------------------------------------------------------------
# Kelly criterion
# --------------------------------------------------------------------------

def kelly_criterion(p: float, b: float, cap: float = 0.25) -> dict:
    """
    f* = (p(b+1) - 1) / b
    p = probability of winning, b = win/loss payoff ratio.
    """
    p = min(max(p, 0.0), 1.0)
    b = max(b, EPS)
    f_star = (p * (b + 1) - 1) / b
    f_star = max(0.0, min(f_star, 1.0))
    capped = min(f_star, cap)
    return {
        "full_kelly": f_star,
        "half_kelly": f_star * 0.5,
        "quarter_kelly": f_star * 0.25,
        "capped_kelly": capped,
        "cap": cap,
    }


# --------------------------------------------------------------------------
# Recursive Bayesian update
# --------------------------------------------------------------------------

def bayesian_update(prior: float, likelihood_success: float, likelihood_fail: float,
                     smoothing: float = 0.15) -> float:
    """
    P(success|evidence) = P(e|success)*P(success) / P(e)
    Smoothed toward 0.5 to avoid overconfidence from small samples.
    """
    prior = min(max(prior, EPS), 1 - EPS)
    evidence = likelihood_success * prior + likelihood_fail * (1 - prior)
    if evidence < EPS:
        posterior = prior
    else:
        posterior = (likelihood_success * prior) / evidence
    posterior = (1 - smoothing) * posterior + smoothing * 0.5
    return float(min(max(posterior, 0.0), 1.0))


# --------------------------------------------------------------------------
# Hurst exponent — Rescaled Range (R/S) analysis
# --------------------------------------------------------------------------

def hurst_exponent(prices: np.ndarray, min_window: int = 8) -> dict:
    prices = np.asarray(prices, dtype=float)
    log_returns = np.diff(np.log(np.maximum(prices, EPS)))
    n = len(log_returns)
    if n < min_window * 2:
        return {"hurst": 0.5, "regime": "insufficient_data"}

    window_sizes = np.unique(np.logspace(np.log10(min_window), np.log10(n // 2), num=10).astype(int))
    rs_values = []
    valid_sizes = []
    for w in window_sizes:
        if w < 2:
            continue
        n_chunks = n // w
        if n_chunks < 1:
            continue
        rs_chunk = []
        for i in range(n_chunks):
            chunk = log_returns[i * w:(i + 1) * w]
            mean = np.mean(chunk)
            dev = np.cumsum(chunk - mean)
            R = np.max(dev) - np.min(dev)
            S = np.std(chunk)
            if S > EPS:
                rs_chunk.append(R / S)
        if rs_chunk:
            rs_values.append(np.mean(rs_chunk))
            valid_sizes.append(w)

    if len(valid_sizes) < 2:
        return {"hurst": 0.5, "regime": "insufficient_data"}

    log_w = np.log(valid_sizes)
    log_rs = np.log(rs_values)
    slope, intercept = np.polyfit(log_w, log_rs, 1)
    h = float(slope)

    if h < 0.45:
        regime = "mean_reverting"
    elif h > 0.55:
        regime = "trending"
    else:
        regime = "random_walk"

    return {"hurst": h, "regime": regime}


# --------------------------------------------------------------------------
# Realized volatility (annualized) — used widely by agents
# --------------------------------------------------------------------------

def realized_volatility(closes: np.ndarray, periods_per_year: int = 252) -> float:
    closes = np.asarray(closes, dtype=float)
    if len(closes) < 2:
        return 0.0
    log_returns = np.diff(np.log(np.maximum(closes, EPS)))
    return float(np.std(log_returns) * math.sqrt(periods_per_year))
