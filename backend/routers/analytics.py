"""Quant analytics endpoints — thin HTTP wrappers around core/math_engine.py."""
from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core import math_engine as me
from backend.core.yf import fetch_history, fetch_quote

router = APIRouter(prefix="/analytics", tags=["analytics"])


class BSRequest(BaseModel):
    S: float = Field(..., gt=0, description="Spot price")
    K: float = Field(..., gt=0, description="Strike price")
    T: float = Field(..., gt=0, description="Time to expiry, in years")
    r: float = Field(0.045, description="Risk-free rate")
    sigma: float = Field(..., gt=0, description="Annualized volatility")
    option_type: str = Field("call", pattern="^(call|put)$")


@router.post("/black-scholes")
async def black_scholes(req: BSRequest):
    price = me.black_scholes(req.S, req.K, req.T, req.r, req.sigma, req.option_type)
    g = me.greeks(req.S, req.K, req.T, req.r, req.sigma, req.option_type)
    return {**price, "greeks": g}


class MCRequest(BaseModel):
    S0: float = Field(..., gt=0)
    mu: float = 0.08
    sigma: float = Field(..., gt=0)
    T: float = Field(1.0, gt=0)
    steps: int = Field(252, ge=10, le=2000)
    sims: int = Field(5000, ge=100, le=50000)


@router.post("/monte-carlo")
async def monte_carlo(req: MCRequest):
    return me.monte_carlo_gbm(req.S0, req.mu, req.sigma, req.T, req.steps, req.sims)


class IVRequest(BaseModel):
    market_price: float = Field(..., gt=0)
    S: float = Field(..., gt=0)
    K: float = Field(..., gt=0)
    T: float = Field(..., gt=0)
    r: float = 0.045
    option_type: str = Field("call", pattern="^(call|put)$")


@router.post("/implied-volatility")
async def implied_volatility(req: IVRequest):
    iv = me.implied_volatility(req.market_price, req.S, req.K, req.T, req.r, req.option_type)
    return {"implied_volatility": iv}


class PortfolioAsset(BaseModel):
    symbol: str
    weight: float = Field(..., ge=0, le=1)
    mu: float = 0.08
    sigma: float = Field(..., gt=0)


class PortfolioMCRequest(BaseModel):
    assets: list[PortfolioAsset]
    correlation: list[list[float]] | None = None
    total_value: float = Field(100_000, gt=0)
    T: float = Field(1.0, gt=0)
    sims: int = Field(3000, ge=100, le=20000)


@router.post("/portfolio-mc")
async def portfolio_mc(req: PortfolioMCRequest):
    n = len(req.assets)
    if n == 0:
        raise HTTPException(400, "Provide at least one asset")
    weights = np.array([a.weight for a in req.assets])
    if abs(weights.sum() - 1.0) > 1e-6:
        weights = weights / weights.sum()
    mus = np.array([a.mu for a in req.assets])
    sigmas = np.array([a.sigma for a in req.assets])
    corr = np.array(req.correlation) if req.correlation else np.eye(n)
    result = me.portfolio_monte_carlo(weights, mus, sigmas, corr, req.total_value, req.T, sims=req.sims)
    return result


@router.get("/hurst/{symbol}")
async def hurst(symbol: str, period: str = "6mo"):
    try:
        df = fetch_history(symbol, period=period)
        if df.empty:
            raise HTTPException(404, f"No data for {symbol}")
        return {"symbol": symbol.upper(), **me.hurst_exponent(df["Close"].to_numpy())}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc))


@router.get("/greeks-surface/{symbol}")
async def greeks_surface(symbol: str, sigma: float = 0.3, r: float = 0.045, option_type: str = "call"):
    try:
        q = fetch_quote(symbol)
        price = float(q.get("price") or 0)
        if price <= 0:
            raise HTTPException(404, f"No live price for {symbol}")
        strikes = np.linspace(price * 0.8, price * 1.2, 9)
        expiries = np.array([7, 30, 60, 90, 180]) / 365
        surface = me.greeks_surface(price, r, sigma, option_type, strikes, expiries)
        return {"symbol": symbol.upper(), "spot": price, "surface": surface}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc))
