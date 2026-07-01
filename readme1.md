# ⬡ ATHENA v2.0 — Autonomous Financial Cognition Platform

**Paper trading only. No real money is ever at risk.**

ATHENA is a free, open-source quantitative paper-trading dashboard that runs a **5-agent reasoning loop** against live market data (via yfinance, no API key required) while also stress-testing strategies at high synthetic throughput via a vectorized numpy simulation engine.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Architecture](#3-architecture)
4. [Directory Structure](#4-directory-structure)
5. [The 5 Agents & 7-Phase Execution Cycle](#5-the-5-agents--7-phase-execution-cycle)
6. [Quant Math Engine](#6-quant-math-engine)
7. [High-Speed Simulator](#7-high-speed-simulator)
8. [API Reference](#8-api-reference)
9. [Frontend Dashboard](#9-frontend-dashboard)
10. [Guardrails & Configuration](#10-guardrails--configuration)
11. [Data Sources](#11-data-sources)
12. [State Layer (Redis / In-Memory)](#12-state-layer-redis--in-memory)
13. [Database & Storage](#13-database--storage)
14. [Authentication & Security](#14-authentication--security)
15. [Testing](#15-testing)
16. [CI/CD](#16-cicd)
17. [Local Development Setup](#17-local-development-setup)
18. [Docker Deployment (Full Stack)](#18-docker-deployment-full-stack)
19. [Render Deployment (Backend + Redis)](#19-render-deployment-backend--redis)
20. [Vercel Deployment (Frontend)](#20-vercel-deployment-frontend)
21. [Render + Vercel End-to-End Guide](#21-render--vercel-end-to-end-guide)
22. [Environment Variables Reference](#22-environment-variables-reference)
23. [Monitoring (Prometheus + Grafana)](#23-monitoring-prometheus--grafana)
24. [Troubleshooting](#24-troubleshooting)
25. [License](#25-license)

---

## 1. Project Overview

ATHENA is a **self-auditing, self-reflective multi-agent paper-trading decision engine**. It combines:

- **5 autonomous agents** with credibility-weighted voting
- **7-phase execution cycle** (PLAN → ANALYZE → RISK → EXECUTE → AUDIT → CONTENT → EXPLAIN)
- **Real quant math** — all indicators, options pricing, Monte Carlo, Kelly criterion, Hurst exponent implemented from scratch with numpy/scipy (no mocked data)
- **High-speed synthetic simulator** — vectorized numpy GBM engine achieving 8,000–250,000+ synthetic trades/sec
- **Free live market data** via yfinance (no API keys required)
- **Hard guardrails** — max drawdown, volatility kill, minimum confidence, risk score ceiling, Kelly cap — all environment-variable tunable
- **Aegis Guard kill switch** — Supervisor Agent has final veto authority
- **No paid services** — completely free to run (no Bloomberg, no Polygon, no paid NLP)

**Key Philosophy:**
- No paid APIs — completely free to run
- No mocked data — all math is real numerical computation
- Transparency — sentiment is labeled as deterministic lexicon, not presented as advanced NLP
- Safety — paper trading only, kill switch, multi-layer guardrails
- Graceful degradation — Redis falls back to memory, Ollama falls back to templates, Prometheus degrades if not installed

---

## 2. Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Frontend** | React | 18.3.x |
| **Frontend Build** | Create React App (react-scripts) | 5.0.x |
| **Charts** | Recharts | 2.13.x |
| **Frontend Server** | nginx (production) | 1.27-alpine |
| **Backend** | Python | 3.12 |
| **Backend Framework** | FastAPI | 0.115.x |
| **Backend Server** | uvicorn | 0.32.x |
| **WebSocket** | websockets | 13.1 |
| **HTTP Client** | httpx | 0.28.x |
| **Numerical Computing** | numpy | 1.26.x |
| **Scientific Computing** | scipy | 1.13.x |
| **Data Analysis** | pandas | 2.2.x |
| **Market Data** | yfinance | 0.2.x |
| **State Store** | Redis (optional, in-memory fallback) | 7.4-alpine |
| **LLM** | Ollama (optional, template fallback) | latest |
| **Monitoring** | Prometheus + Grafana | optional |
| **Containerization** | Docker & Docker Compose | — |
| **CI/CD** | GitHub Actions | — |
| **Cloud Deployment** | Render (backend + Redis) + Vercel (frontend) | — |

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    React Dashboard (Port 80)                        │
│  ┌──────────┬──────────┬──────────┬────────────┬───────┬─────────┐ │
│  │War Room  │Backtest  │Analytics │Fundamentals│Agents │  Risk   │ │
│  │(Market   │(Simulator│(QuantLab)│            │(Audit │ (Risk   │ │
│  │ Watch)   │ Control) │          │            │  Log)  │ Matrix) │ │
│  └────┬─────┴────┬─────┴────┬─────┴─────┬──────┴───┬───┴─────────┘ │
│       │          │          │           │          │               │
│       └──────────┴──────────┴───────────┴──────────┘               │
│                              │                                     │
│                    nginx Reverse Proxy                              │
│                    /api/ -> backend:8000                            │
│                    /ws/  -> backend:8000 (WebSocket)                │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                     FastAPI Backend (Port 8000)                      │
│                                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌───────────┐  │
│  │ /data/*  │ │ /trade/* │ │/analytics│ │/risk/*  │ │/simulate/*│  │
│  │ Quotes,  │ │ 5-Agent  │ │  BS, MC, │ │Guardrail│ │Vectorized │  │
│  │ History, │ │ 7-Phase  │ │  Greeks, │ │Dashboard│ │GBM Engine │  │
│  │Funds,... │ │  Loop    │ │  Hurst   │ │KillSwtch│ │  Control  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬────┘ └─────┬─────┘  │
│       │            │            │            │            │         │
│       └────────────┴────────────┴────────────┴────────────┘         │
│                              │                                      │
│                    Core Engine Layer                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐              │
│  │math_engine│ │  yf.py   │ │state.py  │ │ sim.py    │              │
│  │ Real     │ │ Yahoo    │ │Redis/    │ │ Vectorized│              │
│  │ Quant    │ │ Finance  │ │In-Memory │ │ GBM       │              │
│  │ Math     │ │ Data     │ │ Store    │ │ Engine    │              │
│  └──────────┘ └──────────┘ └────┬─────┘ └───────────┘              │
│                                  │                                  │
└──────────────────────────────────┼──────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │  Redis   │  │  Ollama  │  │Prometheus│
              │  State + │  │  LLM     │  │ Metrics  │
              │  Pub/Sub │  │(Optional)│  │(Optional)│
              └──────────┘  └──────────┘  └─────┬────┘
                                                │
                                          ┌─────▼────┐
                                          │  Grafana  │
                                          │(Optional) │
                                          └──────────┘
```

### Two Clearly Separated Data Paths:

1. **Live Path** (`/trade/execute`): Real yfinance prices + full 5-agent reasoning. Cadence is bound by the free yfinance API (~15s effective cache).
2. **Synthetic Path** (`/simulate/*`): Vectorized GBM tick generation. Processes thousands of synthetic fills per second via numpy batch computation. No real data, no real money.

---

## 4. Directory Structure

```
athena/
├── .env                          # Live environment variables (gitignored)
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
├── README.md                     # Project README
├── docker-compose.yml            # Full stack Docker Compose (6 services)
│
├── backend/                      # FastAPI Python backend
│   ├── __init__.py
│   ├── main.py                   # FastAPI entrypoint, CORS, router mounts
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile                # Backend Docker image (python:3.12-slim)
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   └── agents.py             # 5 agents (Trader, Analyst, Risk, Supervisor, Content)
│   │                             # + AgenticLoop orchestrator (7-phase cycle)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── ai.py                 # Ollama LLM client (async httpx)
│   │   ├── math_engine.py        # All quant math (indicators, BS, MC, Kelly, Hurst, etc.)
│   │   ├── simulator.py          # High-speed vectorized GBM simulation engine
│   │   ├── state.py              # Redis/in-memory state store + pub/sub
│   │   └── yf.py                 # Yahoo Finance data fetcher (REST + yfinance)
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── ai.py                 # /ai/* — Ollama status & model management
│   │   ├── analytics.py          # /analytics/* — BS pricer, MC, IV, Hurst, Greeks surface
│   │   ├── data.py               # /data/* — quotes, history, fundamentals, sentiment, macro, options
│   │   ├── risk.py               # /risk/* — guardrail status + kill switch
│   │   ├── simulate.py           # /simulate/* — high-speed synthetic engine control
│   │   ├── trade.py              # /trade/* — agentic cycle execution
│   │   └── ws.py                 # /ws/live — WebSocket live event stream
│   │
│   └── tests/
│       ├── __init__.py
│       └── test_math_engine.py   # 16 tests (all real math, no mocks)
│
├── frontend/                     # React dashboard
│   ├── package.json              # Node dependencies
│   ├── Dockerfile                # Multi-stage build (node:20 build → nginx serve)
│   ├── nginx.conf                # nginx config (SPA + API proxy + WS proxy)
│   ├── public/
│   │   └── index.html            # HTML entrypoint
│   └── src/
│       ├── index.js              # React entrypoint
│       ├── index.css             # Global dark quant-terminal theme
│       ├── App.js                # Main app shell, navigation, status bar
│       ├── api.js                # API client (REST + WebSocket hook)
│       └── components/
│           ├── shared.jsx        # Shared UI components (Card, Pill, StatBox, etc.)
│           ├── WarRoom.jsx       # Market watch, OHLCV chart, trade execution
│           ├── Simulator.jsx     # High-speed synthetic backtest controls
│           ├── QuantLab.jsx      # Black-Scholes pricer + Monte Carlo
│           ├── Fundamentals.jsx  # Company fundamentals, sentiment, Hurst, macro
│           ├── Agents.jsx        # Per-agent reasoning log viewer
│           └── RiskMatrix.jsx    # Guardrail dashboard, kill switch, equity curve
│
├── deploy/
│   ├── DEPLOY.md                 # Brief deployment guide
│   ├── render.yaml               # Render Blueprint (PaaS deployment)
│   └── .github/
│       └── workflows/
│           └── ci.yml            # GitHub Actions CI pipeline
│
├── monitoring/
│   ├── prometheus.yml            # Prometheus scrape config
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/
│       │   │   └── datasource.yml
│       │   └── dashboards/
│       │       └── dashboard.yml
│       └── dashboards/
│           └── athena.json       # Pre-built Grafana dashboard
│
└── scripts/
    └── setup.sh                  # One-command setup script
```

---

## 5. The 5 Agents & 7-Phase Execution Cycle

### Agent Credibility Weights

| Agent | Credibility | Role |
|-------|-------------|------|
| **TraderAgent** | 0.70 | Computes 8 technical indicators → directional vote |
| **AnalystAgent** | 0.82 | Bayesian p_trade update + Kelly sizing + Expected Value |
| **RiskAgent** | 0.88 | Monte Carlo VaR/CVaR/Sharpe → composite risk score 0-100 |
| **SupervisorAgent (Aegis Guard)** | 0.95 | Checks all guardrails, final veto authority |
| **ContentAgent** | 0.78 | Deterministic narrative (Ollama fallback) |

### 7-Phase Execution Cycle

```
Phase 1:  PLAN     → TraderAgent reads market data, computes 8 indicators,
                      votes BUY/SELL/HOLD based on RSI, MACD, Bollinger,
                      Stochastic, Williams %R, CCI, VWAP, ATR

Phase 2:  ANALYZE  → AnalystAgent applies Bayesian update (recursive prior),
                      computes Kelly criterion (capped), Expected Value,
                      reads Hurst exponent for trend regime classification

Phase 3:  RISK     → RiskAgent runs Monte Carlo GBM simulation (2000 paths),
                      computes VaR 95%, CVaR 95%, Sharpe, Sortino,
                      generates composite risk score 0-100

Phase 4:  EXECUTE  → Paper equity updated with simulated P&L based on
                      Kelly-sized position and estimated volatility move

Phase 5:  AUDIT    → SupervisorAgent (Aegis Guard) evaluates ALL guardrails:
                      - Drawdown check
                      - Volatility kill check
                      - Minimum confidence check
                      - Risk score ceiling check
                      - Kill switch status
                      Can override any trade → HOLD

Phase 6:  CONTENT  → ContentAgent generates plain-English narrative
                      (Ollama LLM when available, deterministic template fallback)

Phase 7:  EXPLAIN  → Explainability module summarizes cycle
                      (Ollama LLM or deterministic summary)
```

### Agent Source Code Location

All agents are defined in `backend/agents/agents.py:10-387`. The `AgenticLoop` class orchestrates the full cycle.

### How the Trader Votes

The TraderAgent evaluates 8 technical indicators:

| Indicator | Function | Vote Contribution |
|-----------|----------|-------------------|
| RSI | `rsi()` | +1 if < 30 (oversold), -1 if > 70 (overbought) |
| MACD Histogram | `macd()` | +1 if positive, -1 if negative |
| Bollinger %B | `bollinger_bands()` | +1 if < 0.05 (below lower), -1 if > 0.95 (above upper) |
| Stochastic %K | `stochastic()` | +1 if < 20 (oversold), -1 if > 80 (overbought) |
| Williams %R | `williams_r()` | +1 if < -80, -1 if > -20 |
| CCI | `cci()` | +1 if < -100, -1 if > 100 |
| VWAP | `vwap()` | +0.5 if price < VWAP, -0.5 if price > VWAP |
| ATR | `atr()` | Used for volatility context |

Final decision: **BUY** if votes >= 2, **SELL** if votes <= -2, **HOLD** otherwise.

---

## 6. Quant Math Engine

All implemented from scratch in `backend/core/math_engine.py:1-434` using numpy/scipy. **Zero mocked data.**

### Technical Indicators

| Function | Description |
|----------|-------------|
| `rsi(closes, period=14)` | Relative Strength Index (Wilder's smoothing), 0-100 scale |
| `bollinger_bands(closes, period=20, num_std=2.0)` | Upper/mid/lower bands + %B + bandwidth |
| `ema(values, period)` | Exponential Moving Average (recursive alpha smoothing) |
| `macd(closes, fast=12, slow=26, signal=9)` | MACD line, signal line, histogram |
| `stochastic(highs, lows, closes, period=14, d_period=3)` | %K and %D oscillators |
| `williams_r(highs, lows, closes, period=14)` | Williams %R (-100 to 0) |
| `cci(highs, lows, closes, period=20)` | Commodity Channel Index |
| `vwap(highs, lows, closes, volumes)` | Volume-Weighted Average Price |
| `atr(highs, lows, closes, period=14)` | Average True Range |
| `all_indicators(highs, lows, closes, volumes)` | All 8 in one pass |

### Black-Scholes & Options

| Function | Description |
|----------|-------------|
| `black_scholes(S, K, T, r, sigma, option_type)` | BS call/put price |
| `greeks(S, K, T, r, sigma, option_type)` | Delta, Gamma, Theta (per day), Vega (per 1%), Rho (per 1%) |
| `implied_volatility(market_price, S, K, T, r, option_type)` | Newton-Raphson with bisection fallback |
| `greeks_surface(S, r, sigma, option_type, strikes, expiries)` | Greeks across strike × expiry grid |

### Monte Carlo

| Function | Description |
|----------|-------------|
| `monte_carlo_gbm(S0, mu, sigma, T, steps, sims)` | GBM simulation → VaR 95%, CVaR 95%, Sharpe, Sortino, p_profit, percentiles, sample paths |
| `portfolio_monte_carlo(weights, mus, sigmas, corr, S0_total, T, steps, sims)` | Correlated multi-asset GBM via Cholesky decomposition |

### Risk Metrics

| Function | Description |
|----------|-------------|
| `kelly_criterion(p, b, cap=0.25)` | Full/half/quarter/capped Kelly fractions |
| `bayesian_update(prior, likelihood_success, likelihood_fail, smoothing=0.15)` | Recursive posterior with smoothing toward 0.5 |
| `hurst_exponent(prices)` | Rescaled Range (R/S) analysis → regime: mean_reverting / trending / random_walk |
| `realized_volatility(closes, periods_per_year=252)` | Annualized standard deviation of log returns |

---

## 7. High-Speed Simulator

Defined in `backend/core/simulator.py:1-211`. A **vectorized synthetic backtest** engine.

### Design Principles

- **No Python-level tick loop** — all computations are numpy vectorized
- **Batch processing** — 2,000–50,000 ticks processed per batch in a single numpy pass
- **Vectorized MA crossover** — signals computed across entire batch at once
- **Deadband filtering** — ignores noise-sized crossovers (configurable bps threshold)
- **Kelly-sized fills** — position sizing applied per synthetic fill
- **Throughput:** 8,000–250,000+ synthetic trades/sec (hardware dependent)
- **Stats published via WebSocket** every ~150ms (never one message per trade)

### SimConfig Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `symbol` | "SYNTH" | Ticker label |
| `s0` | 100.0 | Starting price |
| `mu` | 0.08 | Annualized drift |
| `sigma` | 0.35 | Annualized volatility |
| `ticks_per_batch` | 2000 | Synthetic ticks per batch |
| `fast_window` | 8 | Fast MA window |
| `slow_window` | 34 | Slow MA window |
| `deadband_bps` | 8.0 | Crossover deadband (basis points) |
| `kelly_fraction` | 0.1 | Kelly fraction for sizing |
| `fee_bps` | 0.5 | Round-trip fee (basis points) |

### SimStats Output

| Field | Description |
|-------|-------------|
| `run_id` | Unique run identifier |
| `elapsed_sec` | Run duration |
| `total_ticks` | Total synthetic ticks processed |
| `total_trades` | Total synthetic trades executed |
| `wins` | Winning trades |
| `losses` | Losing trades |
| `win_rate` | Win/loss ratio |
| `equity` | Current paper equity |
| `max_drawdown_pct` | Maximum drawdown percentage |
| `last_price` | Last synthetic price |
| `trades_per_sec` | Instantaneous trades/second |
| `avg_ticks_per_sec` | Average ticks/second |
| `equity_curve_tail` | Last 200 equity curve points |

---

## 8. API Reference

### Root & Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root info (name, version, docs link) |
| GET | `/health` | Health check: status, uptime, state backend, mode |
| GET | `/metrics` | Prometheus metrics (if instrumentator installed) |

### Data Routes (`/data/*`)

| Method | Path | Parameters | Description |
|--------|------|------------|-------------|
| GET | `/data/quote/{symbol}` | symbol | Live quote (price, day high/low, volume, market cap, currency) |
| GET | `/data/history/{symbol}` | symbol, period=3mo, interval=1d | OHLCV history as DataFrame |
| GET | `/data/fundamentals/{symbol}` | symbol | P/E, forward P/E, P/B, ROE, beta, dividend yield, market cap, 52w high/low |
| GET | `/data/sentiment/{symbol}` | symbol | Lexicon-scored news headline sentiment (compound, positive, negative, neutral) |
| GET | `/data/macro` | — | VIX, 10Y yield, DXY, gold, oil |
| GET | `/data/options/{symbol}` | symbol | Full options chain (calls + puts with strikes, expiries, IV, Greeks) |

### Trade Routes (`/trade/*`)

| Method | Path | Parameters | Description |
|--------|------|------------|-------------|
| POST | `/trade/execute` | symbol=AAPL | Run full 7-phase agent cycle |
| GET | `/trade/history` | limit=100 | Past trade cycle records |
| GET | `/trade/logs` | limit=300 | Per-agent phase logs |
| POST | `/trade/reset` | — | Wipe history, reset equity/priors, deactivate kill switch |

### Analytics Routes (`/analytics/*`)

| Method | Path | Parameters | Description |
|--------|------|------------|-------------|
| POST | `/analytics/black-scholes` | body: {S, K, T, r, sigma, option_type} | BS price + Greeks (delta, gamma, theta, vega, rho) |
| POST | `/analytics/monte-carlo` | body: {S0, mu, sigma, T, steps, sims} | GBM MC simulation (VaR, CVaR, Sharpe, Sortino) |
| POST | `/analytics/implied-volatility` | body: {market_price, S, K, T, r, option_type} | Newton-Raphson IV solver |
| POST | `/analytics/portfolio-mc` | body: {weights, mus, sigmas, corr, S0_total, T, steps, sims} | Correlated multi-asset MC |
| GET | `/analytics/hurst/{symbol}` | symbol | Hurst exponent + regime classification |
| GET | `/analytics/greeks-surface/{symbol}` | symbol, param | Greeks across strikes x expiries |

### AI Routes (`/ai/*`)

| Method | Path | Parameters | Description |
|--------|------|------------|-------------|
| GET | `/ai/status` | — | Ollama connection status + available models |
| POST | `/ai/pull` | body: {model} | Pull an Ollama model |

### Risk Routes (`/risk/*`)

| Method | Path | Parameters | Description |
|--------|------|------------|-------------|
| GET | `/risk/status` | — | Live guardrail dashboard + equity curve + kill switch status |
| POST | `/risk/kill-switch` | activate=bool | Toggle Aegis Guard kill switch on/off |

### Simulate Routes (`/simulate/*`)

| Method | Path | Parameters | Description |
|--------|------|------------|-------------|
| POST | `/simulate/configure` | body: SimConfig fields | Set simulator parameters |
| POST | `/simulate/start` | — | Start synthetic engine |
| POST | `/simulate/stop` | — | Stop synthetic engine |
| POST | `/simulate/reset` | — | Reset simulator state |
| GET | `/simulate/stats` | — | Live throughput/simulation stats |

### WebSocket

| Path | Description |
|------|-------------|
| WS `/ws/live` | Live event stream (trades, sim stats, kill switch toggles, resets) |

The WebSocket forwards every event published via Redis pub/sub (or in-memory equivalent). Event types:
- `trade_executed` — Full trade cycle result
- `sim_stats` — Live simulator throughput stats
- `kill_switch` — Kill switch toggle events
- `reset` — System reset events

### Frontend API Client

The frontend API client is in `frontend/src/api.js:1-87`. It exposes:
- `api.health()`, `api.quote(symbol)`, `api.history(symbol)`, `api.fundamentals(symbol)`, `api.sentiment(symbol)`, `api.macro()`, `api.options(symbol)`
- `api.executeTrade(symbol)`, `api.tradeHistory()`, `api.tradeLogs()`, `api.resetTrade()`
- `api.blackScholes(body)`, `api.monteCarlo(body)`, `api.hurst(symbol)`, `api.greeksSurface(symbol)`
- `api.riskStatus()`, `api.killSwitch(activate)`
- `api.simConfigure(cfg)`, `api.simStart()`, `api.simStop()`, `api.simReset()`, `api.simStats()`
- `useLiveFeed()` React hook — WebSocket auto-connect with exponential backoff, returns `{ connected, lastEvent, simStats }`

By default `API_BASE` points to `http://localhost:8000` (dev) or is set via `REACT_APP_API_BASE`.

---

## 9. Frontend Dashboard

### Dashboard Tabs

| Tab | Component | File | Description |
|-----|-----------|------|-------------|
| **MARKET WATCH** | WarRoom | `WarRoom.jsx` | Live chart (OHLCV via Recharts), trade execution button, decision stream |
| **BACKTEST** | Simulator | `Simulator.jsx` | Control the high-speed synthetic engine (start/stop, config sliders, live stats) |
| **ANALYTICS** | QuantLab | `QuantLab.jsx` | Interactive Black-Scholes pricer + Monte Carlo simulation controls |
| **FUNDAMENTALS** | Fundamentals | `Fundamentals.jsx` | Company fundamentals (P/E, P/B, ROE, beta), sentiment, Hurst regime, macro data |
| **AUDIT LOG** | Agents | `Agents.jsx` | Per-agent reasoning logs, credibility bars, phase-by-phase breakdown |
| **RISK** | RiskMatrix | `RiskMatrix.jsx` | Live guardrail dashboard, kill switch toggle, equity curve chart |

### Shared UI Components (`shared.jsx`)

- `Card` — Bordered container with title
- `Pill` — Colored status badge
- `StatBox` — Label + value display
- `DataTable` — Styled table component

### Theme

- **Fonts:** JetBrains Mono (monospace) + Inter (sans-serif) from Google Fonts
- **Dark theme** with CSS custom properties:
  - `--void`: #0D1117 (page background)
  - `--surface`: #161B22 (panel background)
  - `--surface-2`: #1C2333 (hover/active)
  - `--hairline`: #30363D (borders)
  - `--text-bright`: #E6EDF3 (primary text)
  - `--text-faint`: #8B949E (muted text)
  - `--signal-buy`: #26A69A (green)
  - `--signal-sell`: #EF5350 (red)
  - `--signal-hold`: #FFA726 (amber)

### Production Build

The frontend Dockerfile (`frontend/Dockerfile`) uses a **multi-stage build**:
1. **Stage 1 (build):** `node:20-alpine` — installs dependencies, builds with `react-scripts`
2. **Stage 2 (serve):** `nginx:1.27-alpine` — copies build output, configures nginx

---

## 10. Guardrails & Configuration

All guardrails are environment-variable tunable — no code changes needed.

### Guardrail Thresholds

| Variable | Default | Description |
|----------|---------|-------------|
| `ATHENA_MAX_DRAWDOWN` | 1.0 | Percent paper equity loss before Supervisor halts all trades |
| `ATHENA_VOL_KILL` | 0.50 | Annualized sigma ceiling — if exceeded, Supervisor blocks trades |
| `ATHENA_MIN_CONFIDENCE` | 0.52 | p_trade floor below which Supervisor defaults to HOLD |
| `ATHENA_MAX_RISK_SCORE` | 70 | Composite 0-100 risk score ceiling from RiskAgent Monte Carlo |
| `ATHENA_KELLY_CAP` | 0.25 | Hard cap on Kelly fraction regardless of edge estimate |

### How Guardrails Are Evaluated

In `backend/agents/agents.py:191-225`, the SupervisorAgent checks:
1. **Kill switch active?** → If yes, all trades blocked
2. **Volatility >= VOL_KILL?** → "VOLATILITY_KILL" violation
3. **p_trade < MIN_CONFIDENCE** and decision is not HOLD? → "MIN_CONFIDENCE" violation
4. **Risk score >= MAX_RISK_SCORE**? → "RISK_SCORE_BREACH" violation
5. **Drawdown >= MAX_DRAWDOWN**? → "MAX_DRAWDOWN" violation
6. If ANY violation → final decision overridden to HOLD

### Ollama LLM Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model to pull and use |
| `OLLAMA_TIMEOUT` | 30 | Request timeout in seconds |
| `OLLAMA_ENABLED` | `true` | Set `false` to skip Ollama entirely |

Ollama is **fully optional**. When disabled (`OLLAMA_ENABLED=false`) or unreachable, the ContentAgent falls back to deterministic template narratives and the Explainability module falls back to a structured summary. The system works perfectly without it.

---

## 11. Data Sources

### Yahoo Finance (yfinance)

| Endpoint | Data | Source File |
|----------|------|-------------|
| `/data/quote/{symbol}` | Live price, day high/low, volume, market cap | `backend/core/yf.py:155-181` |
| `/data/history/{symbol}` | OHLCV history (period, interval configurable) | `backend/core/yf.py:124-153` |
| `/data/fundamentals/{symbol}` | P/E, P/B, ROE, beta, market cap, 52w high/low | `backend/core/yf.py:183-246` |
| `/data/sentiment/{symbol}` | Lexicon-scored news headline sentiment | VADER-based deterministic scorer |
| `/data/macro` | VIX, 10Y yield, DXY, gold, oil | yfinance ETFs |
| `/data/options/{symbol}` | Full options chain (calls + puts) | yfinance options |

### Key Details

- **No API keys required** for any data source
- **No paid APIs** — completely free to run
- All data is **delayed** (free tier) — not tick-level real-time
- Yahoo Finance has a ~15s effective cache on free tier
- Sentiment is a **deterministic lexicon scorer** (not advanced NLP)
- Rate limiting is handled with retry + exponential backoff (429 errors)

### Yahoo Finance Session Management

In `backend/core/yf.py:26-107`:
- Shared `requests.Session` with browser-like User-Agent
- Cookie pre-warming via `https://finance.yahoo.com/`
- Crumb-based authentication for fundamentals endpoint
- Automatic crumb refresh every 600 seconds
- 3 retry attempts with exponential backoff on rate limits (429)

---

## 12. State Layer (Redis / In-Memory)

Defined in `backend/core/state.py:1-158`.

### Design

- Wraps Redis for cross-process shared state (trade history, agent logs, risk status, sim stats)
- Pub/sub for WebSocket fan-out
- **Automatic in-memory fallback** if Redis is unreachable

### Backend Selection

At startup (`state.py:79-91`):
1. Attempts Redis connection with 1.5s timeout
2. On success → uses Redis (returns "redis" from `backend` property)
3. On failure → uses in-memory `_MemoryBackend` (returns "memory")

### In-Memory Fallback (`_MemoryBackend`)

- `dict` for key-value storage
- `deque` (maxlen=5000) for list storage
- `asyncio.Queue` for pub/sub subscribers
- Full API parity with Redis client

### Stored Data

| Key | Type | Description |
|-----|------|-------------|
| `trade:history` | List | Trade cycle records (max 5000) |
| `trade:logs` | List | Per-agent phase logs (max 5000) |
| `risk:status` | JSON | Guardrail state and equity curve |
| `sim:config` | JSON | Simulator configuration |
| `sim:stats` | JSON | Live simulator stats |

---

## 13. Database & Storage

ATHENA has **no persistent database**. All state is stored in:
- **Redis** (when available) — ephemeral, survives container restarts via Docker volume
- **In-memory** (fallback) — lost on process restart

This is by design:
- No data to persist (paper trading only)
- No user accounts
- No historical database dependencies
- Zero configuration to get started

For production use with Redis, data persists in the `redis_data` Docker volume.

---

## 14. Authentication & Security

### Current State

ATHENA has **no authentication system**:
- No user accounts
- No login/password
- No API keys
- No JWT tokens
- No session management

### Security Considerations

- **Paper trading only** — no real money at risk
- **No sensitive data stored** — no passwords, no financial credentials
- **CORS middleware** restricts origins (configurable via `CORS_ORIGINS`)
- **Kill switch** can halt all trading remotely
- All Yahoo Finance data is public
- No database with user data

### CORS Configuration

In `backend/main.py:32-39`:
```python
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, ...)
```

For production, set `CORS_ORIGINS` to your Vercel frontend URL.

---

## 15. Testing

### Test Suite

16 tests in `backend/tests/test_math_engine.py:1-133`:

| Test | Description |
|------|-------------|
| `test_rsi_bounds` | RSI output is 0-100 |
| `test_bollinger_band_ordering` | lower ≤ mid ≤ upper |
| `test_macd_runs` | MACD returns all 3 fields |
| `test_all_indicators_complete` | All 8 indicators present |
| `test_black_scholes_call_put_parity` | Put-call parity holds |
| `test_black_scholes_call_positive` | Call price > 0 |
| `test_greeks_delta_bounds` | Call delta 0-1, Put delta -1-0 |
| `test_implied_volatility_recovers_input` | IV solver recovers known sigma |
| `test_monte_carlo_shape` | MC returns valid stats |
| `test_kelly_criterion_capped` | Capped Kelly ≤ cap |
| `test_kelly_zero_edge_no_position` | Zero edge → zero position |
| `test_bayesian_update_smoothing` | Posterior pulled up but < 1.0 |
| `test_hurst_exponent_range` | Hurst in valid range |
| `test_realized_volatility_nonnegative` | Vol ≥ 0 |
| `test_agentic_loop_runs_end_to_end` | Full 7-phase cycle with all agents |
| `test_simulator_batch_is_vectorized_and_fast` | 5000 ticks in < 1 second |

### Running Tests

```bash
# All tests
python -m pytest backend/tests -v

# Specific test
python -m pytest backend/tests/test_math_engine.py::test_black_scholes_call_put_parity -v

# With coverage (requires pytest-cov)
python -m pytest backend/tests -v --cov=backend
```

---

## 16. CI/CD

### GitHub Actions

Defined in `deploy/.github/workflows/ci.yml:1-29`:

```yaml
name: ATHENA CI
on:
  push: [main, develop]
  pull_request: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - Python 3.12 setup (with pip cache)
      - pip install -r backend/requirements.txt
      - pytest backend/tests -v --tb=short
      - Import smoke test
```

The CI pipeline:
- Runs on every push to `main`/`develop` and PRs to `main`
- Installs Python dependencies from `requirements.txt`
- Runs all 16 tests
- Verifies the backend imports correctly

---

## 17. Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- npm
- Docker & Docker Compose (optional, for full stack)

### Backend Setup

```bash
# Navigate to project root
cd athena

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Run backend (Redis not needed — auto-falls-back to in-memory)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# API docs at http://localhost:8000/docs
# Health at http://localhost:8000/health
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install --legacy-peer-deps

# Start development server (points to local backend)
REACT_APP_API_BASE=http://localhost:8000 npm start

# Opens at http://localhost:3000
```

### Running Tests

```bash
# From project root
python -m pytest backend/tests -v
```

### Running Full Stack with Docker

```bash
# One-command setup
./scripts/setup.sh

# Or manually
docker compose up --build -d
```

### URLs After Local Launch

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:80 |
| API docs (Swagger) | http://localhost:8000/docs |
| API docs (ReDoc) | http://localhost:8000/redoc |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin / athena_admin) |

---

## 18. Docker Deployment (Full Stack)

### Architecture

The `docker-compose.yml` (96 lines) defines 6 services:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `redis` | `redis:7.4-alpine` | 6379 | State store + pub/sub |
| `backend` | Built from `backend/Dockerfile` | 8000 | FastAPI backend |
| `frontend` | Built from `frontend/Dockerfile` | 80 | React + nginx |
| `ollama` | `ollama/ollama` | 11434 | LLM server |
| `prometheus` | `prom/prometheus:v2.55.0` | 9090 | Metrics collection |
| `grafana` | `grafana/grafana:11.3.0` | 3001 | Dashboard visualization |

### Dockerfiles

**Backend** (`backend/Dockerfile:1-19`):
- Base: `python:3.12-slim`
- Installs `requirements.txt`
- Copies `backend/` directory
- Exposes port 8000
- Healthcheck at `/health`
- Runs `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1`

**Frontend** (`frontend/Dockerfile:1-16`):
- Stage 1: `node:20-alpine` — `npm install --legacy-peer-deps`, `npm run build`
- Stage 2: `nginx:1.27-alpine` — copies build output + nginx config
- Exposes port 80

### nginx Configuration (`frontend/nginx.conf:1-31`)

```nginx
# WebSocket proxy
location /ws/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}

# REST API proxy — strips /api prefix
location /api/ {
    proxy_pass http://backend:8000/;
}

# SPA fallback
location / {
    try_files $uri $uri/ /index.html;
}
```

### Docker Compose Networking

- Services communicate via Docker Compose internal network
- `frontend` proxies `/api/` to `backend:8000` and `/ws/` to `backend:8000`
- `backend` connects to `redis:6379` and `ollama:11434`
- `prometheus` scrapes `backend:8000/metrics`
- `grafana` connects to `prometheus:9090`

### Deployment Steps

```bash
# 1. Clone
git clone https://github.com/YOUR_USER/athena.git
cd athena

# 2. Configure environment
cp .env.example .env
# Edit .env as needed

# 3. Build and start
docker compose up --build -d

# 4. View logs
docker compose logs -f backend

# 5. Stop
docker compose down

# 6. Stop and remove volumes
docker compose down -v
```

---

## 19. Render Deployment (Backend + Redis)

### Overview

Render provides a free tier that hosts:
- **Backend:** Python web service (512 MB RAM, auto-sleeps after 15 min inactivity)
- **Redis:** Free 25MB Redis instance

### Prerequisites

1. A [Render](https://render.com) account
2. Your project pushed to a GitHub repository

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USER/athena.git
git push -u origin main
```

### Step 2: Create Backend Service on Render

#### Method A: Using Render Blueprint (Recommended)

Render Blueprint uses `deploy/render.yaml` to auto-configure both services:

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Select the `deploy/render.yaml` file
5. Click **"Apply"**
6. Both `athena-backend` and `athena-redis` will be created automatically

#### Method B: Manual Setup

**Create Redis:**
1. Click **"New +"** → **"Redis"**
2. Name: `athena-redis`
3. Plan: **Free** ($0/month)
4. Click **"Create Redis"**
5. Copy the **"Internal Connection String"** (starts with `redis://...`)

**Create Web Service:**
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:

| Field | Value |
|-------|-------|
| Name | `athena-backend` |
| Runtime | **Python** |
| Build Command | `pip install -r backend/requirements.txt` |
| Start Command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| Plan | **Free** |
| Health Check Path | `/health` |

4. Click **"Advanced"** → **"Add Environment Variables"**

### Step 3: Configure Environment Variables

Add these environment variables in Render:

| Variable | Value | Notes |
|----------|-------|-------|
| `REDIS_URL` | `redis://...` (from Redis instance) | Use Internal Connection String |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | Update after Vercel deploy |
| `OLLAMA_ENABLED` | `false` | Required — Ollama cannot run on Render |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ignored when OLLAMA_ENABLED=false |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ignored when OLLAMA_ENABLED=false |
| `OLLAMA_TIMEOUT` | `30` | Ignored when OLLAMA_ENABLED=false |
| `PYTHON_VERSION` | `3.12.0` | (Optional, Render auto-detects) |

### Step 4: Deploy

Click **"Create Web Service"**. Render will:
1. Clone your repository
2. Install Python dependencies
3. Start uvicorn on the assigned `$PORT`
4. Run health checks on `/health`
5. Show live logs

Once deployed, note your backend URL: `https://athena-backend.onrender.com`

### Step 5: Verify Backend

```bash
# Test health endpoint
curl https://athena-backend.onrender.com/health

# Expected response:
{"status":"ok","uptime_sec":123.45,"state_backend":"redis","mode":"paper_trading_only"}

# Test API docs
# Visit: https://athena-backend.onrender.com/docs
```

### Render Free Tier Limitations

- **Auto-sleep:** Service sleeps after 15 minutes of inactivity
- **Warm-up delay:** First request after sleep takes ~30-60 seconds
- **Bandwidth:** 100 GB/month outbound
- **CPU/RAM:** Shared, 512 MB RAM
- **Custom domains:** Not available on free tier
- **Redis:** 25 MB maxmemory
- **No persistent disk:** Use Redis for persistent state

To prevent sleep, you can use a cron-job service (e.g., cron-job.org, UptimeRobot) to ping `/health` every 10 minutes.

---

## 20. Vercel Deployment (Frontend)

### Overview

Vercel hosts the React frontend as a static site with:
- Global CDN
- Automatic HTTPS
- Custom domain support
- Free tier (100 GB bandwidth, 100 deployments/day)

### Step 1: Configure Frontend for Production

The frontend nginx config (`frontend/nginx.conf`) proxies `/api/` and `/ws/` to the backend. **Vercel does NOT use nginx** — it serves static files directly.

For Vercel, the frontend needs to know the backend URL at build time.

### Step 2: Deploy to Vercel

#### Method A: Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Navigate to frontend directory
cd frontend

# Deploy
vercel --prod
```

#### Method B: Vercel Dashboard

1. Go to [Vercel Dashboard](https://vercel.com)
2. Click **"Add New..."** → **"Project"**
3. Import your GitHub repository
4. Configure:

| Setting | Value |
|---------|-------|
| Framework Preset | **Create React App** |
| Root Directory | `frontend/` |
| Build Command | `npm run build` (default) |
| Output Directory | `build` (default) |
| Node.js Version | 20.x |

5. **Environment Variables**:

| Variable | Value |
|----------|-------|
| `REACT_APP_API_BASE` | `https://athena-backend.onrender.com` |

6. Click **"Deploy"**

### Step 3: Post-Deployment

Vercel will provide a URL like `https://athena-dashboard.vercel.app`.

### Step 4: Update CORS on Backend

After Vercel deploys, update the `CORS_ORIGINS` environment variable on Render:

```
CORS_ORIGINS=https://athena-dashboard.vercel.app
```

This is critical — without it, browser CORS errors will block all API calls.

### Step 5: Verify Frontend

1. Visit your Vercel URL
2. The dark terminal-themed dashboard should load
3. The status bar should show **CONNECTED** (WebSocket connection to backend)
4. Try executing a trade (War Room tab, enter a symbol like AAPL, click Execute)

### Vercel Free Tier Limitations

- **Serverless functions:** 100 GB-hours/month
- **Bandwidth:** 100 GB/month
- **Build minutes:** 6,000 minutes/month
- **Concurrent builds:** 1
- **Custom domains:** Supported (add in Vercel dashboard)

### Important Notes for Vercel

1. **No nginx:** Vercel serves static files directly. The nginx.conf is only used in Docker deployment.
2. **API calls go directly to Render:** The frontend uses `REACT_APP_API_BASE` to know the backend URL.
3. **WebSocket connects to Render:** The WebSocket URL is derived from the backend URL.
4. **Build-time env vars:** `REACT_APP_API_BASE` must be set at build time (Vercel injects it).
5. **CORS is essential:** The backend must allow the Vercel domain.

---

## 21. Render + Vercel End-to-End Guide

### Complete Step-by-Step Deployment

#### Phase 1: Prepare

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USER/athena.git
cd athena

# 2. Review the deploy blueprint
cat deploy/render.yaml
# This defines both backend & Redis on Render
```

#### Phase 2: Deploy Backend (Render)

**Option A: Blueprint (Automated)**

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Blueprint"**
3. Connect GitHub → Select repo → Select `deploy/render.yaml`
4. Click **"Apply"**
5. Wait for both services to deploy (~3-5 minutes)
6. Note your backend URL: `https://athena-backend.onrender.com`

**Option B: Manual**

1. Create Redis instance:
   - Name: `athena-redis`
   - Plan: Free
   - Note the Internal Connection String

2. Create Web Service:
   - Name: `athena-backend`
   - Runtime: Python
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1`
   - Health Check Path: `/health`
   - Plan: Free
   - Env Variables:
     - `REDIS_URL`: (paste Redis Internal Connection String)
     - `CORS_ORIGINS`: `https://athena-dashboard.vercel.app` (update later)
     - `OLLAMA_ENABLED`: `false`
     - `PYTHON_VERSION`: `3.12.0`

3. Click **"Create Web Service"**
4. Wait for deploy to complete (~5 minutes)
5. Verify: `curl https://athena-backend.onrender.com/health`

#### Phase 3: Deploy Frontend (Vercel)

1. Go to [Vercel Dashboard](https://vercel.com)
2. Click **"Add New..."** → **"Project"**
3. Import your GitHub repository
4. Configure:
   - Framework Preset: **Create React App**
   - Root Directory: `frontend/`
   - Build Command: `npm run build`
   - Output Directory: `build`
5. Add Environment Variable:
   - `REACT_APP_API_BASE`: `https://athena-backend.onrender.com`
6. Click **"Deploy"**
7. Wait for deployment (~2-3 minutes)
8. Note your Vercel URL: `https://athena-dashboard.vercel.app`

#### Phase 4: Connect Frontend ↔ Backend

1. Go back to **Render Dashboard**
2. Select **`athena-backend`** web service
3. Go to **"Environment"** tab
4. Edit `CORS_ORIGINS`:
   - Change to: `https://athena-dashboard.vercel.app`
   - If you want to test locally too: `https://athena-dashboard.vercel.app,http://localhost:3000`
5. Click **"Save Changes"**
6. Render will automatically redeploy

#### Phase 5: Verify Full Stack

1. Visit `https://athena-dashboard.vercel.app`
2. **Check status bar:** Should show "CONNECTED" (green)
3. **War Room tab:**
   - Enter a symbol (e.g., `AAPL`)
   - Click **"Execute"**
   - Wait ~5-10 seconds
   - See the agent decision result
4. **Backtest tab:**
   - Click **"Start"** to run the simulator
   - Watch live TPS (trades per second) in status bar
5. **Analytics tab:**
   - Try Black-Scholes pricing
   - Try Monte Carlo simulation
6. **Fundamentals tab:**
   - Enter a symbol to see fundamentals, sentiment, macro
7. **Audit Log tab:**
   - View per-agent reasoning from executed trades
8. **Risk tab:**
   - View guardrail status
   - Toggle kill switch

#### Phase 6: Keep Backend Warm (Optional)

Render free tier sleeps after 15 minutes of inactivity. To prevent sleep:

1. Go to [cron-job.org](https://cron-job.org)
2. Create a free account
3. Create a cron job:
   - URL: `https://athena-backend.onrender.com/health`
   - Interval: Every 10 minutes
4. This keeps the backend "warm" (doesn't cost anything)

#### Phase 7: Custom Domain (Optional)

**Vercel:**
1. Go to Project → Settings → Domains
2. Add your custom domain
3. Configure DNS (CNAME to `cname.vercel-dns.com`)

**Render:**
- Free tier does not support custom domains
- Upgrade to Pro ($7/month) for custom domain support

---

## 22. Environment Variables Reference

### Core Configuration

| Variable | Required | Default | Location | Description |
|----------|----------|---------|----------|-------------|
| `REDIS_URL` | No | `redis://localhost:6379/0` | `backend/core/state.py:21` | Redis connection string. Falls back to in-memory if unavailable |
| `CORS_ORIGINS` | No | `http://localhost:3000` | `backend/main.py:32` | Comma-separated allowed origins |
| `PORT` | No | `8000` | Render injected | Render assigns port automatically |

### Ollama LLM

| Variable | Required | Default | Location | Description |
|----------|----------|---------|----------|-------------|
| `OLLAMA_ENABLED` | No | `true` | `backend/agents/agents.py:23` | Set `false` to disable Ollama |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | `backend/core/ai.py:18` | Ollama server URL |
| `OLLAMA_MODEL` | No | `llama3.2:3b` | `backend/core/ai.py:19` | Model to use |
| `OLLAMA_TIMEOUT` | No | `30` | `backend/core/ai.py:20` | Request timeout in seconds |

### Guardrails

| Variable | Default | Location | Description |
|----------|---------|----------|-------------|
| `ATHENA_MAX_DRAWDOWN` | `1.0` | `backend/agents/agents.py:31` | % equity loss before halt |
| `ATHENA_VOL_KILL` | `0.50` | `backend/agents/agents.py:32` | Annualized sigma ceiling |
| `ATHENA_MIN_CONFIDENCE` | `0.52` | `backend/agents/agents.py:33` | p_trade floor |
| `ATHENA_MAX_RISK_SCORE` | `70` | `backend/agents/agents.py:34` | Risk score ceiling (0-100) |
| `ATHENA_KELLY_CAP` | `0.25` | `backend/agents/agents.py:35` | Kelly fraction cap |

### Frontend

| Variable | Required | Default | Location | Description |
|----------|----------|---------|----------|-------------|
| `REACT_APP_API_BASE` | No | `http://localhost:8000` | `frontend/src/api.js:3` | Backend API URL |

### Required for Cloud Deployment

For Render + Vercel deployment, you must set:

**Render (Backend):**
```
REDIS_URL=<from Render Redis instance>
CORS_ORIGINS=https://athena-dashboard.vercel.app
OLLAMA_ENABLED=false
PYTHON_VERSION=3.12.0
```

**Vercel (Frontend):**
```
REACT_APP_API_BASE=https://athena-backend.onrender.com
```

---

## 23. Monitoring (Prometheus + Grafana)

### Overview

ATHENA includes an optional monitoring stack via Docker Compose. This is for Docker deployments only — not available on Render.

### Prometheus (`monitoring/prometheus.yml`)

- Scrapes `backend:8000/metrics` every 5 seconds
- Data retention: 7 days
- Exposed on port 9090

### Grafana

- Pre-configured Prometheus datasource
- Auto-provisioned dashboard (`monitoring/grafana/dashboards/athena.json`)
- Login: `admin` / `athena_admin`
- Exposed on port 3001

### Backend Metrics

Prometheus instrumentation is optional. The backend tries to import `prometheus_fastapi_instrumentator` at startup:
- If installed → `/metrics` endpoint is enabled
- If not installed → warning logged, `/metrics` disabled
- The `requirements.txt` includes `prometheus-fastapi-instrumentator==7.0.0`

### Accessing Metrics

```bash
# Direct
curl http://localhost:8000/metrics

# Via Prometheus
curl http://localhost:9090/api/v1/query?query=...

# Via Grafana
http://localhost:3001 (admin / athena_admin)
```

---

## 24. Troubleshooting

### Backend Won't Start

**Problem:** `uvicorn backend.main:app --reload` fails
**Solution:**
```bash
# Ensure you're in the right directory
cd athena

# Ensure dependencies are installed
pip install -r backend/requirements.txt

# Check Python version
python --version  # must be 3.12+

# Try without reload
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Redis Connection Error

**Problem:** `StateStore: Redis unavailable` warning
**Solution:** This is **normal** for local dev. The system falls back to in-memory automatically. For production, ensure `REDIS_URL` is correctly set.

### CORS Errors in Browser

**Problem:** Browser console shows CORS errors
**Solution:**
```bash
# 1. Check CORS_ORIGINS on backend
# 2. Ensure it includes your frontend URL exactly (no trailing slash)
# 3. For local dev: CORS_ORIGINS=http://localhost:3000
# 4. For Render + Vercel: CORS_ORIGINS=https://athena-dashboard.vercel.app
```

### Yahoo Finance 429 Errors

**Problem:** `Yahoo rate-limited (429)` in logs
**Solution:**
- Built-in retry with exponential backoff handles this
- Yahoo free tier has rate limits (~100 requests/minute)
- The system auto-retries up to 3 times
- For heavy use, add longer delays between requests

### Frontend Shows "DISCONNECTED"

**Problem:** Status bar shows DISCONNECTED
**Solution:**
```bash
# 1. Check backend is running
curl http://localhost:8000/health  # or your Render URL

# 2. Check WebSocket URL
# For local: frontend connects to ws://localhost:80/ws/live (via nginx)
# For Vercel: frontend connects to wss://athena-backend.onrender.com/ws/live

# 3. Check nginx (Docker) or CORS (Render)
# 4. Check browser console for WebSocket errors
```

### Ollama Not Working

**Problem:** ContentAgent shows template narratives instead of AI-generated
**Solution:**
```bash
# 1. Check if Ollama is running
curl http://localhost:11434/api/tags

# 2. Check OLLAMA_ENABLED is true
# 3. Check OLLAMA_BASE_URL is correct
# 4. For Render: OLLAMA cannot run there — set OLLAMA_ENABLED=false
```

### Render Backend Slow First Request

**Problem:** First request after idle takes 30-60 seconds
**Solution:** This is **normal** for Render free tier. Use a cron-job service (e.g., cron-job.org) to ping `/health` every 10 minutes to keep it warm.

### npm Install Fails

**Problem:** `npm install` in frontend directory fails
**Solution:**
```bash
# Use --legacy-peer-deps (required for react-scripts 5.x)
cd frontend
npm install --legacy-peer-deps

# If still failing, clear cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

### Docker Build Fails

**Problem:** `docker compose up --build` fails
**Solution:**
```bash
# 1. Ensure Docker Desktop is running
# 2. Check Docker version
docker --version
docker compose version

# 3. Rebuild without cache
docker compose build --no-cache

# 4. Check logs
docker compose logs backend
```

### Trade Execution Returns 502

**Problem:** POST `/trade/execute?symbol=AAPL` returns 502
**Solution:**
```
1. Yahoo Finance may be temporarily blocked
2. The symbol may not exist on Yahoo Finance
3. Check backend logs for the specific error
4. Try a different symbol (e.g., SPY, MSFT, GOOGL)
```

### WebSocket Disconnects

**Problem:** WebSocket keeps disconnecting
**Solution:**
```bash
# 1. Check nginx WebSocket proxy config (Docker)
#    frontend/nginx.conf should have:
#    proxy_set_header Upgrade $http_upgrade;
#    proxy_set_header Connection "upgrade";

# 2. Check backend WebSocket endpoint
#    backend/routers/ws.py

# 3. The frontend has auto-reconnect with exponential backoff
#    (1s, 2s, 4s, 8s, max 10s)
```

---

## 25. License

MIT License. Free forever. No paid APIs required to run.

---

## Quick Reference

### One-Command Local Start
```bash
git clone https://github.com/YOUR_USER/athena.git && cd athena && ./scripts/setup.sh
```

### One-Command Tests
```bash
python -m pytest backend/tests -v
```

### One-Command Cloud Deploy
1. Push to GitHub
2. Render: Import `deploy/render.yaml` as Blueprint
3. Vercel: Import `frontend/` as project, set `REACT_APP_API_BASE` to Render URL
4. Update `CORS_ORIGINS` on Render to Vercel URL

### Essential URLs
| Service | Local | Render + Vercel |
|---------|-------|----------------|
| Dashboard | http://localhost:80 | https://athena-dashboard.vercel.app |
| API | http://localhost:8000 | https://athena-backend.onrender.com |
| API Docs | http://localhost:8000/docs | https://athena-backend.onrender.com/docs |
| Health | http://localhost:8000/health | https://athena-backend.onrender.com/health |
