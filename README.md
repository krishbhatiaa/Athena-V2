# ⬡ ATHENA v2.0

**Autonomous Financial Cognition Platform** — a self-auditing, multi-agent paper-trading war room.

> **Paper trading only. No real money is ever at risk.**

ATHENA is a free, open-source quantitative trading dashboard that runs a 5-agent reasoning loop against live market data (via yfinance, no API key required) while also stress-testing the strategy at high synthetic throughput via a vectorized simulation engine.
DEMO:

Uploading athenav2DEMO (1) (1) (1).mp4…


---

## Features

| Feature | Detail |
|---|---|
| 5-agent reasoning loop | Trader → Analyst → RiskAgent → Supervisor (Aegis Guard) → ContentAgent |
| 7-phase execution cycle | PLAN → ANALYZE → RISK → EXECUTE → AUDIT → CONTENT → EXPLAIN |
| Real quant math | RSI, MACD, Bollinger, Stochastic, CCI, VWAP, ATR, Williams %R; Black-Scholes, Greeks, Monte Carlo GBM, Kelly criterion, Hurst exponent, Bayesian update |
| Synthetic high-speed sim | Vectorized numpy GBM — 8,000–250,000+ synthetic trades/sec (stress-testing, not a live feed) |
| Free live data | yfinance — quotes, history, fundamentals, options chains, macro (VIX, 10Y, gold, oil) |
| Hard guardrails | Max drawdown, vol kill, min confidence, risk score ceiling, Kelly cap — all env-variable tunable |
| Kill switch | Aegis Guard blocks all execution; toggle from the Risk Matrix tab or API |
| Zero paid services | No Bloomberg, no Polygon, no paid NLP. Sentiment = deterministic lexicon. Content = template engine. |
| Prometheus + Grafana | Optional observability stack included in `docker-compose.yml` |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USER/athena.git && cd athena

# 2. Launch everything
./scripts/setup.sh

# Dashboard  → http://localhost:80
# API docs   → http://localhost:8000/docs
# Grafana    → http://localhost:3001  (admin / athena_admin)
```

No API keys needed.

---

## Architecture

```
React Dashboard (JetBrains Mono + Inter, dark quant-terminal aesthetic)
 ├─ War Room        live chart, execute agent cycle, decision stream
 ├─ Simulator       control the high-speed synthetic engine
 ├─ Quant Lab       interactive Black-Scholes pricer + Monte Carlo
 ├─ Fundamentals    P/E, P/B, ROE, beta, macro, Hurst, sentiment
 ├─ Agents          per-agent reasoning logs, credibility bars
 └─ Risk Matrix     live guardrails, kill switch, equity curve

FastAPI backend (Python 3.12)
 ├─ /data/*         yfinance quotes, history, fundamentals, options, macro
 ├─ /trade/*        agentic loop execution against live data
 ├─ /analytics/*    Black-Scholes, Monte Carlo, IV, Hurst, Greeks surface
 ├─ /risk/*         guardrail status + kill switch
 ├─ /simulate/*     high-speed synthetic GBM engine
 └─ /ws/live        WebSocket — live event fan-out

State layer
 └─ Redis (or automatic in-memory fallback for local dev)
```

---

## Agents

| Agent | Credibility | Role |
|---|---|---|
| **Trader** | 0.70 | 8 technical indicators → directional vote |
| **Analyst** | 0.82 | Bayesian p_trade + Kelly sizing + EV |
| **RiskAgent** | 0.88 | Monte Carlo VaR/CVaR/Sharpe → composite risk score |
| **Supervisor (Aegis Guard)** | 0.95 | Checks all guardrails; final veto authority |
| **ContentAgent** | 0.78 | Deterministic narrative (no LLM required) |

---

## What "thousands of trades per second" means

The **Simulator tab** processes synthetic ticks in vectorized numpy batches — no Python-level per-tick loop. This achieves 8,000–250,000+ synthetic fills/sec and is explicitly designed to stress-test the strategy logic and infrastructure, not to stream real market data. Free public APIs cannot supply real tick data at that rate.

The **War Room's Execute button** runs against real (delayed, free) yfinance prices. One cycle takes a few seconds — bounded by the API, not the math engine.

---

## Guardrail thresholds

All tunable via environment variables (no code change needed):

```bash
ATHENA_MAX_DRAWDOWN=1.0      # % paper equity loss before halt
ATHENA_VOL_KILL=0.50         # annualized sigma ceiling
ATHENA_MIN_CONFIDENCE=0.52   # p_trade floor
ATHENA_MAX_RISK_SCORE=70     # composite 0-100 ceiling
ATHENA_KELLY_CAP=0.25        # hard Kelly fraction cap
```

---

## API endpoints (summary)

| Method | Path | Description |
|---|---|---|
| GET | `/data/quote/{symbol}` | Live quote |
| GET | `/data/history/{symbol}` | OHLCV history |
| GET | `/data/fundamentals/{symbol}` | P/E, P/B, ROE, beta… |
| GET | `/data/sentiment/{symbol}` | Lexicon-scored news headlines |
| GET | `/data/macro` | VIX, 10Y yield, DXY, gold, oil |
| GET | `/data/options/{symbol}` | Full options chain |
| POST | `/trade/execute?symbol=AAPL` | Run the full 7-phase agent cycle |
| GET | `/trade/history` | Past trade cycle records |
| GET | `/trade/logs` | Per-agent phase logs |
| POST | `/analytics/black-scholes` | BS price + Greeks |
| POST | `/analytics/monte-carlo` | GBM MC simulation |
| POST | `/analytics/implied-volatility` | Newton-Raphson IV solve |
| GET | `/analytics/hurst/{symbol}` | Hurst exponent + regime |
| GET | `/risk/status` | Live guardrail dashboard |
| POST | `/risk/kill-switch?activate=bool` | Toggle Aegis Guard |
| POST | `/simulate/start` | Start high-speed synthetic engine |
| GET | `/simulate/stats` | Live throughput stats |
| WS | `/ws/live` | Real-time event stream |

Full interactive docs at `/docs`.

---

## Development

```bash
# Tests (16 tests, all real math — no mocks)
python -m pytest backend/tests -v

# Backend only (no Docker, Redis auto-falls-back to in-memory)
uvicorn backend.main:app --reload

# Frontend only
cd frontend && npm install --legacy-peer-deps && npm start
```

---

## Deployment

See [`deploy/DEPLOY.md`](deploy/DEPLOY.md) for:
- Docker Compose (full stack)
- Render + Vercel (free tier cloud)
- Fly.io
- Railway

---

## License

MIT. Free forever. No paid APIs required to run.
