# ARIA — Autonomous Revenue Intelligence Agent

> *Every rupee that slips away leaves a trace. ARIA reads that trace, reasons over it, and wins the money back — with proof.*

Razorpay AI Buildathon · Track 03 — AI Revenue Recovery.

ARIA detects revenue at risk across payment, checkout, subscription, and receivables
surfaces; reasons over root cause with an LLM diagnostic chain; executes bounded,
reversible recovery actions; measures actual money recovered as a P&L; and proves
every decision in an append-only audit ledger.

See [`BUILD_PLAN.md`](./BUILD_PLAN.md) for the phased 10-day build plan.

---

## Tech stack

- **Backend:** FastAPI · Pydantic v2 · SQLAlchemy 2 (async) · Alembic · Celery + Redis
- **LLM:** provider-agnostic — **Groq** (`llama-3.3-70b-versatile`, free) primary,
  local **Ollama** (`qwen2.5:7b`) fallback; embeddings via `nomic-embed-text`
- **Data:** PostgreSQL 16 · Redis 7
- **Frontend:** React + TypeScript + Vite · Tailwind + shadcn/ui · Tremor · Recharts/Nivo · Framer Motion
- **Infra:** Docker Compose · GitHub Actions

## What's real vs simulated (honesty box)

| Area | This build |
|---|---|
| Payment events | **Razorpay test mode** (real webhooks) **+ synthetic injector** as the guaranteed demo path |
| Messaging (WhatsApp/SMS/email) | **Simulated** — rendered to an `outbox` and shown in the dashboard; no real sends |
| Voice/IVR | Script + SSML **preview only**; no live calls |
| LLM | Real inference via Groq (free) or local Ollama |

---

## Quick start

### 1. Configure
```bash
cp .env.example .env
# Fill in GROQ_API_KEY (free: https://console.groq.com) — or set LLM_PROVIDER=ollama for fully local.
# Generate a PII key:  python -c "import secrets;print(secrets.token_urlsafe(32))"
```

### 2. Run everything (Docker)
```bash
docker compose up --build
# API:   http://localhost:8000      Docs: http://localhost:8000/docs
# Health: http://localhost:8000/health   Readiness: http://localhost:8000/health/ready
```
> Ollama (if used) runs on the **host**; containers reach it via `host.docker.internal:11434`.

### 3. Frontend (dev)
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api → backend)
```

---

## Local development (without Docker)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate     |  bash:  source .venv/Scripts/activate
pip install -r requirements.txt

# Start Postgres + Redis via Docker only:
docker compose up -d postgres redis

# API (reload):
uvicorn app.main:app --reload

# Celery worker / beat (separate shells):
celery -A app.core.celery_app.celery_app worker --loglevel=info
celery -A app.core.celery_app.celery_app beat --loglevel=info
```

### Useful commands
```bash
pytest -q                       # tests
ruff check . && ruff format .   # lint + format
python scripts/check_llm.py     # verify the configured LLM provider responds
alembic revision --autogenerate -m "msg"   # new migration (Phase 1+)
alembic upgrade head            # apply migrations
```

---

## Repo layout

```
app/
  api/         FastAPI routers (health; recovery/audit/config land in later phases)
  agents/      LLM client + (Phase 2) orchestrator & sub-agents
  detection/   (Phase 1) risk scoring & detection engine
  execution/   (Phase 3) bounded action executors
  models/      SQLAlchemy ORM models
  schemas/     Pydantic API/agent contracts
  core/        config · logging · db · celery
alembic/       migrations
prompts/       (Phase 2) versioned YAML prompts
frontend/      React + Vite dashboard
scripts/       dev utilities (check_llm, seed, inject …)
tests/
```

## Project phases

| Phase | Theme |
|---|---|
| **P0** | Scaffolding & infra ✅ |
| P1 | Ingestion + detection |
| P2 | Agent intelligence (reasoning) |
| P3 | Execution + Recovery P&L |
| P4 | Hinglish + B2B receivables + human-in-loop |
| P5 | Dashboard (design-led) |
| P6 | Seed data, demo polish |

Full detail in [`BUILD_PLAN.md`](./BUILD_PLAN.md).
