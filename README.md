# ARIA — Autonomous Revenue Intelligence Agent

> *Every rupee that slips away leaves a trace. ARIA reads that trace, reasons over it, and wins the money back — with proof.*

Razorpay AI Buildathon · Track 03 — AI Revenue Recovery.

ARIA detects revenue at risk across payment, checkout, subscription, and receivables
surfaces; reasons over root cause with an LLM diagnostic chain; executes bounded,
reversible recovery actions; measures actual money recovered as a P&L; and proves
every decision in an append-only audit ledger.

## Architecture

```
Razorpay test webhooks ─┐
                        ├─► Ingestion ─► Detection ─► Orchestrator ─► Execution ─► Outcome Tracker
Synthetic injector  ────┘   (idempotent) (6-signal    (CheckPolicy    (bounded     (attribution →
                                          risk score)   → Diagnose      action        Recovery P&L)
                                                         → Intervene     executors)
                                                         → Execute|Escalate)
                                                              │
                        Postgres (state + append-only audit ledger)  ·  Redis (idempotency, locks, bank-rate)
                                                              │
                                          FastAPI REST  ◄──►  React dashboard (Command Center, Reasoning
                                                              Stream, Action Queue, P&L Sankey, Audit, Outbox)
```

- **Agents** (Groq/Ollama, provider-agnostic): a deterministic **stopping-rules gate** runs
  first, then a **Diagnostic** agent (visible chain-of-thought), an **Intervention Selector**
  (bounded action space + Hinglish generation), and an **Escalation** agent — wired as an
  explicit, fully-audited state machine.
- **Every decision writes to the audit ledger** with a SHA-256 checksum.

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
| **Recovery loop** | **Real** — ARIA issues a real **Razorpay test-mode payment link**; a real payment fires a real webhook back through a tunnel, and ARIA attributes the recovery to the diagnosed case (real payment reference, 1.0 attribution) |
| Payment events (failures) | **Razorpay test webhooks** + a synthetic injector as the guaranteed demo path |
| Messaging (WhatsApp/SMS/email) | **Simulated** — rendered to an `outbox` shown in the dashboard; no real sends |
| Voice/IVR | Hinglish script + SSML **preview only**; no live calls |
| Batch backdrop | **Seeded** 30-day dataset (deterministic) for scale; the P&L math is real |
| LLM | Real inference via Groq (free) or local Ollama |

---

## Quick start

### 1. Configure
```bash
cp .env.example .env
# Fill in GROQ_API_KEY (free: https://console.groq.com) — or set LLM_PROVIDER=ollama for fully local.
# Generate a PII key:  python -c "import secrets;print(secrets.token_urlsafe(32))"
```

### 2. Datastores + schema + demo data
```bash
docker compose up -d postgres redis            # host ports 5433 (pg) / 6380 (redis)
.venv/Scripts/python -m alembic upgrade head   # create schema
.venv/Scripts/python scripts/seed.py           # ~6s: 30-day backdrop, no LLM calls
```

### 3. API + dashboard
```bash
# API — if :8000 is taken locally, use another port and point the dashboard at it:
.venv/Scripts/python -m uvicorn app.main:app --port 8010

cd frontend && npm install
VITE_API_TARGET=http://localhost:8010 npm run dev   # http://localhost:5173
```
Open **http://localhost:5173**, hit **Fire event** on the Command Center, then click a Risk
Event to watch the reasoning stream.

> Ollama (if used) runs on the **host**; containers reach it via `host.docker.internal:11434`.
> To run the whole stack (api + worker + beat) in Docker instead: `docker compose up --build`.

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
  api/         FastAPI routers (health, webhooks, dev, risk-events, recovery,
               invoices, ptp, escalations, outbox, dashboard)
  agents/      provider-agnostic LLM client, orchestrator, sub-agents, policy, prompts
  detection/   6-signal risk scorer, taxonomy, bank-rate, workflow classifier, aging scanner
  execution/   bounded action executors, dispatcher, outcome tracker, PTP checks
  analytics/   Recovery P&L computation
  ingestion/   dual-path ingestion, normalizer, scenarios, invoice CSV import
  integrations/ Razorpay signature verification
  tasks/       Celery tasks (detection, orchestration, outcome, promises)
  models/      SQLAlchemy ORM models  ·  schemas/  Pydantic contracts
  core/        config · logging · db · celery · crypto · audit · redis · bootstrap
alembic/       migrations          prompts/  versioned YAML prompts
frontend/      React + Vite dashboard
scripts/       check_llm · inject · seed · sample_invoices.csv
tests/
```

## Project phases — all complete

| Phase | Theme | Status |
|---|---|---|
| P0 | Scaffolding & infra | ✅ |
| P1 | Dual-path ingestion + detection engine | ✅ |
| P2 | Agent intelligence (visible reasoning) | ✅ |
| P3 | Execution + Recovery P&L | ✅ |
| P4 | Hinglish + B2B receivables + human-in-loop | ✅ |
| P5 | Design-led dashboard | ✅ (UI polish pass pending) |
| P6 | Seed data, demo script, docs | ✅ |
