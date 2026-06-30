from __future__ import annotations

import logging
import threading
import time
from functools import lru_cache

import numpy as np
import pandas as pd
import requests
import yfinance as yf

logger = logging.getLogger("athena.yf")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Shared session & crumb
# ---------------------------------------------------------------------------

def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    for attempt in range(3):
        try:
            resp = s.get("https://finance.yahoo.com/", timeout=15)
            resp.raise_for_status()
            if s.cookies:
                break
        except Exception as exc:
            logger.warning("Yahoo pre-warm attempt %d failed: %s", attempt + 1, exc)
        if attempt < 2:
            time.sleep(2 ** attempt)
    if not s.cookies:
        logger.warning("No cookies received from Yahoo; data fetching may fail")
    else:
        logger.debug("Yahoo session initialized (cookies: %s)", list(s.cookies.keys()))
    return s


@lru_cache(maxsize=1)
def _session() -> requests.Session:
    return _make_session()


_crumb_cache: str | None = None
_crumb_ts: float = 0
_CRUMB_TTL = 600  # seconds
_crumb_lock = threading.Lock()


def _fetch_crumb() -> str | None:
    s = _session()
    for attempt in range(3):
        r = s.get(
            "https://query1.finance.yahoo.com/v1/test/getcrumb",
            headers={"Referer": "https://finance.yahoo.com/"},
            timeout=15,
        )
        if r.status_code == 200:
            logger.info("Yahoo crumb obtained")
            return r.text
        if r.status_code == 429:
            logger.warning("Yahoo crumb rate-limited (429), retry %d", attempt + 1)
            time.sleep(2 ** attempt * 3)
        else:
            logger.warning("Yahoo crumb error %d: %s", r.status_code, r.text[:100])
            break
    return None


def _crumb() -> str | None:
    global _crumb_cache, _crumb_ts
    with _crumb_lock:
        if _crumb_cache is None or time.time() - _crumb_ts > _CRUMB_TTL:
            _crumb_cache = _fetch_crumb()
            _crumb_ts = time.time()
        return _crumb_cache


def _invalidate_crumb():
    global _crumb_cache, _crumb_ts
    with _crumb_lock:
        _crumb_cache = None
        _crumb_ts = 0


def _request(url: str, params: dict | None = None, retries: int = 2) -> requests.Response:
    s = _session()
    headers = {"Referer": "https://finance.yahoo.com/"}
    for attempt in range(retries + 1):
        r = s.get(url, params=params, headers=headers, timeout=30)
        if r.status_code != 429:
            return r
        logger.warning("Yahoo rate-limited (429), retry %d/%d", attempt + 1, retries)
        time.sleep(2 ** attempt * 5)
    return s.get(url, params=params, headers=headers, timeout=30)


_PERIOD_MAP = {
    "1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo",
    "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y", "10y": "10y", "max": "max",
}
_INTERVAL_MAP = {
    "1m": "1m", "2m": "2m", "5m": "5m", "15m": "15m", "30m": "30m",
    "60m": "60m", "90m": "90m", "1h": "60m",
    "1d": "1d", "5d": "5d", "1wk": "1wk", "1mo": "1mo", "3mo": "3mo",
}


# ---------------------------------------------------------------------------
# Public helpers — no yfinance dependency
# ---------------------------------------------------------------------------

def fetch_history(symbol: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    r = _request(
        "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol.upper(),
        params={
            "range": _PERIOD_MAP.get(period, period),
            "interval": _INTERVAL_MAP.get(interval, interval),
            "includePrePost": "false",
        },
    )
    if r.status_code != 200:
        raise ValueError(f"Yahoo chart API returned {r.status_code} for {symbol}: {r.text[:200]}")
    data = r.json()
    result = data["chart"]["result"]
    if not result:
        error = data["chart"].get("error")
        raise ValueError(f"No data for {symbol}: {error}")
    quotes = result[0]
    timestamps = quotes["timestamp"]
    ohlcv = quotes["indicators"]["quote"][0]
    df = pd.DataFrame({
        "Open": ohlcv["open"],
        "High": ohlcv["high"],
        "Low": ohlcv["low"],
        "Close": ohlcv["close"],
        "Volume": ohlcv["volume"],
    }, index=pd.to_datetime(timestamps, unit="s"))
    df = df.dropna()
    df.index.name = "Date"
    return df


def fetch_quote(symbol: str) -> dict:
    r = _request(
        "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol.upper(),
        params={"range": "1d", "interval": "1d", "includePrePost": "true"},
    )
    if r.status_code != 200:
        raise ValueError(f"Yahoo chart API returned {r.status_code} for {symbol}: {r.text[:200]}")
    data = r.json()
    result = data["chart"]["result"]
    if not result:
        error = data["chart"].get("error")
        raise ValueError(f"No data for {symbol}: {error}")
    meta = result[0]["meta"]
    ohlcv = result[0]["indicators"]["quote"][0]
    price = meta.get("regularMarketPrice")
    return {
        "symbol": symbol.upper(),
        "price": price or 0,
        "previous_close": meta.get("previousClose") or meta.get("chartPreviousClose") or 0,
        "day_high": meta.get("regularMarketDayHigh") or 0,
        "day_low": meta.get("regularMarketDayLow") or 0,
        "volume": meta.get("regularMarketVolume") or (ohlcv.get("volume") or [0])[-1] or 0,
        "market_cap": meta.get("marketCap"),
        "currency": meta.get("currency"),
        "name": meta.get("longName") or meta.get("shortName"),
    }


def fetch_fundamentals(symbol: str) -> dict:
    crumb = _crumb()
    if not crumb:
        raise ValueError("Could not obtain Yahoo crumb")
    s = _session()
    r = s.get(
        "https://query1.finance.yahoo.com/v10/finance/quoteSummary/" + symbol.upper(),
        params={
            "modules": "assetProfile,financialData,defaultKeyStatistics,summaryDetail,quoteType",
            "corsDomain": "finance.yahoo.com",
            "formatted": "false",
            "symbol": symbol.upper(),
            "crumb": crumb,
        },
        headers={"Referer": "https://finance.yahoo.com/"},
        timeout=30,
    )
    if r.status_code == 401:
        _invalidate_crumb()
        crumb = _crumb()
        if not crumb:
            raise ValueError("Could not obtain fresh Yahoo crumb")
        r = s.get(
            "https://query1.finance.yahoo.com/v10/finance/quoteSummary/" + symbol.upper(),
            params={
                "modules": "assetProfile,financialData,defaultKeyStatistics,summaryDetail,quoteType",
                "corsDomain": "finance.yahoo.com",
                "formatted": "false",
                "symbol": symbol.upper(),
                "crumb": crumb,
            },
            headers={"Referer": "https://finance.yahoo.com/"},
            timeout=30,
        )
    if r.status_code != 200:
        raise ValueError(f"Yahoo quoteSummary returned {r.status_code} for {symbol}: {r.text[:200]}")
    data = r.json()
    qs = data["quoteSummary"]["result"][0]
    qt = qs.get("quoteType", {}) or {}
    ap = qs.get("assetProfile", {}) or {}
    fd = qs.get("financialData", {}) or {}
    sd = qs.get("summaryDetail", {}) or {}
    dk = qs.get("defaultKeyStatistics", {}) or {}

    def _r(v):
        if isinstance(v, dict):
            return v.get("raw")
        return v

    return {
        "symbol": symbol.upper(),
        "name": qt.get("longName") or qt.get("shortName"),
        "sector": ap.get("sector"),
        "industry": ap.get("industry"),
        "pe_ratio": _r(fd.get("trailingPE")),
        "forward_pe": _r(fd.get("forwardPE")),
        "pb_ratio": _r(sd.get("priceToBook")),
        "roe": _r(fd.get("returnOnEquity")),
        "beta": _r(sd.get("beta")),
        "dividend_yield": _r(sd.get("dividendYield")),
        "market_cap": _r(sd.get("marketCap")),
        "52w_high": _r(sd.get("fiftyTwoWeekHigh")),
        "52w_low": _r(sd.get("fiftyTwoWeekLow")),
    }


def get_ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol, session=_session())
