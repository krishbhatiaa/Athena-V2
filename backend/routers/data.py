"""
Market data endpoints. Uses yfinance — free, no API key, but rate-limited
and delayed (not tick-level). All prices are real; sentiment is a
deterministic lexicon scorer (no paid NLP API needed) clearly labeled
as such rather than presented as something it isn't.
"""
from __future__ import annotations

import asyncio
import time

import numpy as np
from fastapi import APIRouter, HTTPException

from backend.core.yf import fetch_fundamentals, fetch_history, fetch_quote, get_ticker

router = APIRouter(prefix="/data", tags=["data"])

_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 30  # seconds


def _cached(key: str):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    return None


def _store(key: str, value: dict):
    _cache[key] = (time.time(), value)


async def _to_thread(fn, *args, **kwargs):
    return await asyncio.to_thread(fn, *args, **kwargs)


async def _yf_call(fn, *args, max_retries=2, **kwargs):
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except Exception as exc:
            err = str(exc)
            if attempt < max_retries and ("429" in err or "Too Many Requests" in err or "Expecting value" in err):
                await asyncio.sleep(2 ** attempt * 2)
                continue
            raise


@router.get("/quote/{symbol}")
async def quote(symbol: str):
    cached = _cached(f"q:{symbol}")
    if cached:
        return cached
    try:
        result = await asyncio.to_thread(fetch_quote, symbol)
        _store(f"q:{symbol}", result)
        return result
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Could not fetch quote for {symbol}: {exc}")


@router.get("/history/{symbol}")
async def history(symbol: str, period: str = "3mo", interval: str = "1d"):
    cached = _cached(f"h:{symbol}:{period}:{interval}")
    if cached:
        return cached
    try:
        df = await asyncio.to_thread(fetch_history, symbol, period, interval)
        if df.empty:
            raise HTTPException(404, f"No history for {symbol}")
        result = {
            "symbol": symbol.upper(),
            "dates": [str(d.date()) for d in df.index],
            "open": df["Open"].round(4).tolist(),
            "high": df["High"].round(4).tolist(),
            "low": df["Low"].round(4).tolist(),
            "close": df["Close"].round(4).tolist(),
            "volume": df["Volume"].astype(int).tolist(),
        }
        _store(f"h:{symbol}:{period}:{interval}", result)
        return result
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Could not fetch history for {symbol}: {exc}")


@router.get("/fundamentals/{symbol}")
async def fundamentals(symbol: str):
    cached = _cached(f"f:{symbol}")
    if cached:
        return cached
    try:
        result = await asyncio.to_thread(fetch_fundamentals, symbol)
        _store(f"f:{symbol}", result)
        return result
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Could not fetch fundamentals for {symbol}: {exc}")


# Tiny deterministic lexicon — transparent, free, no external NLP service required.
_POS_WORDS = {"beat", "beats", "surge", "rally", "growth", "upgrade", "strong",
              "record", "outperform", "bullish", "gain", "soar", "profit"}
_NEG_WORDS = {"miss", "misses", "plunge", "crash", "downgrade", "weak", "loss",
              "underperform", "bearish", "decline", "lawsuit", "fraud", "recall"}


@router.get("/sentiment/{symbol}")
async def sentiment(symbol: str):
    """
    Headline-based sentiment using a transparent lexicon scorer over yfinance
    news. This is NOT a paid NLP API — by design, so the system stays free.
    Swap in NewsAPI + VADER, or a HuggingFace FinBERT call, for richer scoring.
    """
    try:
        t = get_ticker(symbol)
        news = await _yf_call(lambda: t.news or [])
        scores = []
        headlines = []
        for item in news[:15]:
            title = (item.get("content") or item).get("title", "") if isinstance(item.get("content"), dict) else item.get("title", "")
            title = title or item.get("title", "")
            if not title:
                continue
            words = set(title.lower().split())
            pos = len(words & _POS_WORDS)
            neg = len(words & _NEG_WORDS)
            score = (pos - neg) / max(1, pos + neg) if (pos or neg) else 0.0
            scores.append(score)
            headlines.append({"title": title, "score": score})
        avg = float(np.mean(scores)) if scores else 0.0
        label = "bullish" if avg > 0.15 else "bearish" if avg < -0.15 else "neutral"
        return {"symbol": symbol.upper(), "score": avg, "label": label,
                "headlines": headlines, "method": "lexicon_v1 (free, deterministic)"}
    except Exception as exc:  # noqa: BLE001
        return {"symbol": symbol.upper(), "score": 0.0, "label": "neutral",
                "headlines": [], "error": str(exc)}


@router.get("/macro")
async def macro():
    """VIX, 10Y yield, dollar index, gold, oil — all via yfinance, no key required."""
    symbols = {"vix": "^VIX", "yield_10y": "^TNX", "dollar_index": "DX-Y.NYB",
               "gold": "GC=F", "oil": "CL=F"}
    cached = _cached("macro")
    if cached:
        return cached

    async def fetch_one(name, sym):
        try:
            q = await asyncio.to_thread(fetch_quote, sym)
            return name, float(q.get("price") or 0)
        except Exception:  # noqa: BLE001
            return name, None

    results = await asyncio.gather(*(fetch_one(n, s) for n, s in symbols.items()))
    result = {name: val for name, val in results}
    _store("macro", result)
    return result


@router.get("/options/{symbol}")
async def options_chain(symbol: str, expiry: str | None = None):
    try:
        t = get_ticker(symbol)
        expiries = await _yf_call(lambda: t.options)
        if not expiries:
            raise HTTPException(404, f"No options chain for {symbol}")
        chosen = expiry if expiry in expiries else expiries[0]
        chain = await _yf_call(t.option_chain, chosen)
        return {
            "symbol": symbol.upper(),
            "expiry": chosen,
            "available_expiries": list(expiries),
            "calls": chain.calls[["strike", "lastPrice", "bid", "ask", "impliedVolatility", "volume", "openInterest"]].fillna(0).to_dict("records"),
            "puts": chain.puts[["strike", "lastPrice", "bid", "ask", "impliedVolatility", "volume", "openInterest"]].fillna(0).to_dict("records"),
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Could not fetch options for {symbol}: {exc}")
