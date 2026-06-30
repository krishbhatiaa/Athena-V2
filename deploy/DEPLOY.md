# ATHENA — Deployment Guide

> Paper trading only. No real money is ever at risk.

## Quick Start (Docker — recommended)

```bash
git clone https://github.com/YOUR_USER/athena.git
cd athena
./scripts/setup.sh
```

Opens:
- Dashboard → http://localhost:80
- API docs → http://localhost:8000/docs
- Grafana → http://localhost:3001 (admin / athena_admin)

---

## Local development (no Docker)

### Backend
```bash
cd athena
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
# Redis is optional — falls back to in-memory automatically.
```

### Frontend
```bash
cd frontend
npm install --legacy-peer-deps
REACT_APP_API_BASE=http://localhost:8000 npm start
# Opens at http://localhost:3000
```

---

## Free cloud hosting

### Option A — Render + Vercel (recommended for free tier)

1. Push to GitHub
2. Connect repo to **Render** → "New Blueprint" → select `deploy/render.yaml`
   - Backend and Redis deploy automatically, free tier
3. Connect frontend to **Vercel** → import repo → set root to `frontend/`
   - Add env var: `REACT_APP_API_BASE=https://athena-backend.onrender.com`
4. Update `CORS_ORIGINS` in Render backend env to your Vercel URL

### Option B — Railway (all-in-one, ~$5/mo after free trial)

```bash
railway up
```

### Option C — Fly.io (generous free allowance)

```bash
fly launch --name athena-backend --dockerfile backend/Dockerfile
fly secrets set REDIS_URL=<your_upstash_redis_url>
fly deploy
```

---

## Optional Ollama LLM integration

Ollama is fully integrated but **gracefully optional**. When running via Docker Compose, the `ollama` service starts automatically, pulls the model, and serves it. The backend auto-detects it.

**To disable:** set `OLLAMA_ENABLED=false` in your environment.  
**Cloud deployments** (Render / Railway / Fly.io): Ollama cannot run on those platforms. Set `OLLAMA_ENABLED=false` — the system works perfectly with deterministic fallback.

| Variable | Default | Meaning |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model to pull and use |
| `OLLAMA_TIMEOUT` | `30` | Request timeout in seconds |
| `OLLAMA_ENABLED` | `true` | Set `false` to skip Ollama entirely |

## Guardrail tuning

All guardrails are env-variable-controlled — no code changes needed:

| Variable | Default | Meaning |
|---|---|---|
| `ATHENA_MAX_DRAWDOWN` | `1.0` | % paper account loss before Supervisor halts all trades |
| `ATHENA_VOL_KILL` | `0.50` | Annualized sigma ceiling — too much market chaos kills trading |
| `ATHENA_MIN_CONFIDENCE` | `0.52` | p_trade floor below which Supervisor defaults to HOLD |
| `ATHENA_MAX_RISK_SCORE` | `70` | Composite 0-100 ceiling from RiskAgent Monte Carlo output |
| `ATHENA_KELLY_CAP` | `0.25` | Hard cap on Kelly fraction regardless of edge estimate |

---

## Architecture summary

```
React Dashboard
      │
      ├── REST  ──► FastAPI (backend/main.py)
      │                  ├── /data/*     yfinance quotes (free, 15s cache)
      │                  ├── /trade/*    5-agent, 7-phase agentic loop
      │                  ├── /analytics  BS pricer, Monte Carlo, Hurst
      │                  ├── /risk/*     guardrail dashboard + kill switch
      │                  └── /simulate/* vectorized GBM high-speed sim
      │
      └── WebSocket ──► /ws/live → Redis pub/sub (or in-memory fallback)
```

**Two clearly-separated data paths:**
- **Live path** (`/trade/execute`): real yfinance prices + full 5-agent reasoning. Cadence is bound by the free yfinance API (15s cache).
- **Synthetic path** (`/simulate/*`): vectorized GBM tick generation. Genuinely processes thousands of synthetic fills per second via numpy batch computation. No real data, no real money.
