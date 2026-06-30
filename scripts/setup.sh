#!/usr/bin/env bash
set -euo pipefail

echo ""
echo "  ⬡  ATHENA v2.0 — Autonomous Financial Cognition Platform"
echo "  ─────────────────────────────────────────────────────────"
echo "  Paper trading only. No real money is ever at risk."
echo ""

# ---- Prerequisites check ------------------------------------------------
if ! command -v docker &>/dev/null; then
  echo "ERROR: Docker is not installed. Install Docker Desktop and try again."
  echo "       https://docs.docker.com/get-docker/"
  exit 1
fi

if ! docker compose version &>/dev/null && ! docker-compose --version &>/dev/null; then
  echo "ERROR: Docker Compose is not installed."
  exit 1
fi

# ---- Env file -----------------------------------------------------------
if [ ! -f .env ]; then
  echo "→ No .env found — copying .env.example to .env"
  cp .env.example .env
  echo "  Edit .env to customize guardrail thresholds before deployment."
fi

# ---- Build and start ----------------------------------------------------
echo "→ Building and starting all services…"
docker compose up --build -d

echo ""
echo "  ✓ ATHENA is running:"
echo ""
echo "    Dashboard  http://localhost:80"
echo "    API docs   http://localhost:8000/docs"
echo "    Prometheus http://localhost:9090"
echo "    Grafana    http://localhost:3001  (user: admin / pass: athena_admin)"
echo ""
echo "  Logs:   docker compose logs -f backend"
echo "  Stop:   docker compose down"
echo ""
