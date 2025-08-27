# Cursor Project Charter — Protectogram (Panic v1) — Telnyx Edition

## 0) What you (Cursor) must do
- Always propose a short **PLAN** first, then show a **DIFF/FILE LIST** and **TEST PLAN** before writing any files.
- Use **testing-first** workflow: create tests/fixtures and schema migrations before app code.
- Never push or deploy without my explicit “APPROVE & RUN” message.
- After each step, print a **CHECKLIST** of what I should review.

---

## 1) Product summary
**App name:** **Protectogram**

**Purpose:** Telegram + Telnyx safety assistant.

**Milestone 1 scope:** **Panic Button v1** only
- Traveler taps Panic in Telegram (UI entirely in Russian).
- Guardians get immediate alert with **«Я беру ответственность»** button.
- Telnyx **call cascade** starts; **DTMF “1”** acknowledges and halts cascade.
- Traveler can cancel panic (**«Отменить тревогу»**) → stops calls and reminders.
- **Russian TTS**: Telnyx `speak` (`language: ru-RU`) plays panic messages.
- Durable timers via APScheduler + Postgres job store.
- Idempotency (Inbox/Outbox).
- Migrations with Alembic.
- Deploy on Fly.io.

**Future scope (final milestone):**
- Panic flow (M1).
- Trip workflows: leaving, ETA, arrival confirmation.
- Live location sharing in Telegram.
- Reversible roles (family, couples).
- Configurable cascades (retries, quiet hours).
- Paid subscriptions (Stripe).
- Admin dashboard with metrics.
- Multilingual (Russian default, Spanish/English later).

---

## 2) Environments & guardrails (lean setup)
- **Local/CI**: tests only, no real calls.
- **Staging** (`protectogram-staging`): prod-like, Telnyx subaccount, spend cap, whitelisted numbers.
- **Prod** (`protectogram-prod`).

**Secrets per env:**
- POSTGRES_URL
- TELEGRAM_BOT_TOKEN
- TELEGRAM_WEBHOOK_SECRET
- TELNYX_API_KEY
- TELNYX_CONNECTION_ID
- APP_ENV (staging|prod)
- SENTRY_DSN (optional)
- FEATURE_PANIC=true

**Staging guardrails:**
- Telnyx subaccount, spend cap, whitelist.
- Telegram bot rejects unknown chats.
- One scheduler machine only.

---

## 3) Technology choices (recommended & justified)
- **FastAPI (0.111+)** → async, webhook-friendly.
- **SQLAlchemy 2.0** → async ORM, long-term.
- **Alembic** → proven migration tool.
- **APScheduler 4.0** + Postgres job store → durable scheduled tasks.
- **Aiogram 3.x** → async Telegram library, Russian UI support.
- **Telnyx-python + HTTPX** → Call Control, TTS, DTMF.
- **pytest 8.x** → reliable test ecosystem.
- **ruff + mypy** → lint & types.
- **Fly.io Machines** → `web` + `scheduler` process groups.
- **uv / poetry** → modern dependency management.

---

## 4) Repository layout
```
.
├── app/
│   ├── api/                # FastAPI routers: health, telegram, telnyx, admin
│   ├── core/               # config, logging, settings, idempotency
│   ├── domain/             # panic logic, cascade policy
│   ├── integrations/
│   │   ├── telegram/       # inbound/outbound
│   │   └── telnyx/         # call control, TTS, DTMF
│   ├── scheduler/          # APScheduler setup
│   ├── storage/            # SQLAlchemy models
│   └── main.py             # app factory
├── migrations/             # Alembic
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
├── Dockerfile
├── fly.toml
├── pyproject.toml
└── README.md
```

---

## 5) Database schema (M1)
Tables:
- **users**: id, telegram_id, phone_e164, display_name, created_at
- **member_links**: id, watcher_user_id, traveler_user_id, status, call_priority, ring_timeout_sec, max_retries, retry_backoff_sec, telegram_enabled, calls_enabled, created_at, updated_at
- **incidents**: id, traveler_user_id, status, created_at, acknowledged_by_user_id, ack_at, canceled_at
- **alerts**: id, incident_id, type, audience_user_id, status, attempts, last_error, created_at, updated_at
- **call_attempts**: id, alert_id, to_e164, telnyx_call_id, attempt_no, result, dtmf_received, started_at, ended_at, error_code
- **inbox_events**: id, provider, provider_event_id UNIQUE, received_at, payload_json, processed_at
- **outbox_messages**: id, channel, idempotency_key UNIQUE, payload_json, status, provider_message_id, created_at, updated_at
- **scheduled_actions**: id, incident_id, action_type, run_at, state, payload_json, created_at, updated_at

Indexes: provider_event_id, idempotency_key, member_links(traveler_user_id, call_priority), call_attempts(alert_id, attempt_no), scheduled_actions(run_at).

---

## 6) API endpoints (M1)
- **GET** `/health/live`
- **GET** `/health/ready`
- **GET** `/metrics`
- **POST** `/telegram/webhook?secret=`
- **POST** `/telnyx/webhook`
- **POST** `/admin/trigger-panic-test`

---

## 7) Behavior (Panic v1)
- Panic → new incident. Telegram message in Russian:
  - «Тревога от {Имя}! Нажмите “Я беру ответственность”.»
- Telnyx call: TTS Russian voice prompt:
  - “Тревога! Срочно свяжитесь с {Имя}. Нажмите 1, чтобы подтвердить.”
- Ack via Telegram button or DTMF 1 → stop cascade, traveler notified.
- Cancel Panic → incident canceled, jobs stopped, watchers notified.
- Reminders: every 120s until ack/cancel.
- Defaults: ring_timeout=25s, retries=2, backoff=60s, total_ring_cap=180s.

---

## 8) Observability
- JSON logs: correlation_id, incident_id.
- Metrics:
  - `panic_incidents_started_total`
  - `panic_acknowledged_total`
  - `panic_canceled_total`
  - `call_attempts_total{result}`
  - `scheduler_job_lag_seconds`
  - `duplicate_inbox_dropped_total`
  - `outbox_sent_total`

---

## 9) Staging setup
1. Create Fly Postgres `protectogram-pg-staging`.
2. Create Fly app `protectogram-staging` (`web`, `scheduler`).
3. Set secrets.
4. Configure Telegram staging webhook.
5. Telnyx subaccount: Spanish DID, webhook `/telnyx/webhook`, whitelist, spend cap.
6. Deploy, run Alembic upgrade, verify `/health`.

---

## 10) Test plan (staging)
- `/health/ready` returns 200.
- Scheduler fires a one-shot job <120s.
- Panic → one Telegram alert + reminders until ack.
- Telnyx call → Russian TTS prompt plays, DTMF 1 ack halts cascade.
- Duplicate inbound event dropped (metric increments).

---

## 11) Cursor workflow — Prompts for each step

### Prompt 1 — Project bootstrap
“Cursor, propose a PLAN to scaffold the Protectogram repo for **Panic v1** (Telnyx edition). Include:
- Dependencies list (latest stable versions).
- File tree.
- Dockerfile & fly.toml process groups (`web`, `scheduler`).
- CI tasks: ruff, mypy, pytest (unit/integration/contract).
- Scripts/Makefile plan.
Do not create files yet—only plan, DIFF, and TEST PLAN. Wait for APPROVE.”

### Prompt 2 — Create migrations & tests
“Cursor, generate Alembic setup and the **initial migration** for schema in §5. Add integration test: spin temp Postgres, run `alembic upgrade head`, assert tables/indexes exist. Show DIFF, explain TESTS, wait for APPROVE.”

### Prompt 3 — Health + scheduler
“Cursor, add `/health/live`, `/health/ready`, `/metrics` and scheduler using Postgres job store. Implement no-op job handler, metric `scheduler_job_lag_seconds`. Add test: scheduled job at T+5s fires after restart. Show DIFF, wait for APPROVE.”

### Prompt 4 — Telegram primitives
“Cursor, implement `/telegram/webhook?secret=`: validate secret, dedupe by update_id, store in `inbox_events`. Add Outbox dispatcher: send one confirmation message in Russian. Contract tests with canned Telegram updates + idempotency checks. Show DIFF, wait for APPROVE.”

### Prompt 5 — Telnyx primitives
“Cursor, implement `/telnyx/webhook`: verify signature, handle call events, DTMF detection, and `speak` action with Russian TTS (`ru-RU`). Record `call_attempts` rows. Add contract tests with signed requests + status callback. Show DIFF, wait for APPROVE.”

### Prompt 6 — Panic domain & cascade
“Cursor, implement Panic flow per §7:
- Create incident.
- Send Telegram alerts («Я беру ответственность»).
- Schedule Telnyx call attempts per policy.
- Handle DTMF 1 + Telegram ack.
- Cancel panic.
Ensure Inbox/Outbox idempotency.
Add tests: cascade order, retries/backoff, ‘ack halts cascade’. Show DIFF, wait for APPROVE.”

### Prompt 7 — Staging deploy & smoke
“Cursor, prepare deployment for `protectogram-staging`:
- Build Docker image.
- Create Fly Postgres + app if missing.
- Define process groups.
- Set secrets interactively.
- Deploy.
- Set Telegram webhook + Telnyx webhook.
- Run smoke tests from §10.
Summarize results. Wait for manual verification.”

---

## 12) Acceptance criteria (M1)
- Tests green in CI.
- Deployed to staging, health checks green.
- Panic works end-to-end: Telegram alert (Russian), Telnyx call with Russian TTS, DTMF 1 halts cascade.
- Duplicate inbound updates don’t duplicate actions.
- Logs & metrics visible; README includes runbook.

---

13) Local & Tests Policy (authoritative for Cursor)

Goal: zero sync/async conflicts, deterministic tests, no local Postgres install required.

A. Local environment

Prefer Testcontainers-Postgres for integration/API tests (no local DB install).

Optional: docker-compose Postgres for manual local runs; tests still use Testcontainers.

Never use SQLite for integration (we rely on Postgres features and APScheduler PG job store).

B. Test tiers & markers

Unit (@pytest.mark.unit): pure Python/domain logic; sync only, no DB or event loop.

Contract (@pytest.mark.contract): Telegram/Telnyx signature verification with canned payloads; sync, no DB/app.

Integration/API (@pytest.mark.integration): FastAPI app + SQLAlchemy async + Alembic-migrated Postgres (Testcontainers); async.

C. Async testing knobs

pytest-asyncio>=0.23 with asyncio_mode=auto in pytest.ini.

Use httpx.AsyncClient with ASGI lifespan; do not use Starlette TestClient.

SQLAlchemy AsyncEngine/AsyncSession only (asyncpg); never import sync Session.

D. Database fixtures (canonical)

Session-scoped Postgres container → produce a DSN.

Alembic upgrade once per session to head.

Function-scoped AsyncSession with nested transaction (SAVEPOINT); rollback after each test for isolation.

E. Scheduler control

App reads SCHEDULER_ENABLED; default false in tests.

One dedicated integration test enables scheduler with short intervals to prove persistence & firing; all other tests keep it disabled.

F. Parallelization

If using pytest-xdist, either run unit/contract in parallel and serialize integration, or give each worker its own containerized DB (Testcontainers handles this automatically).

G. Do-not list (hard rules)

Do not mix sync and async DB layers.

Do not start APScheduler in every test run.

Do not share one global DB session across tests without savepoints.

Do not hit external networks in tests (Telegram/Telnyx). Use fixtures.

---

## 14) Migrations Policy

Goal: decouple migrations from app settings, support multiple environments, prevent CI failures.

A. Database URL resolution (order of precedence)

1. **CLI argument**: `alembic -x db_url=postgresql://...` (highest priority)
2. **Environment variable**: `ALEMBIC_DATABASE_URL=postgresql://...`
3. **Config file**: `alembic.ini` `sqlalchemy.url` (fallback only)

B. Implementation requirements

- `migrations/env.py` must NOT import `app.core.config` or load `.env` files
- Use `context.get_x_argument(as_dictionary=True)` for CLI args
- Use `os.environ.get("ALEMBIC_DATABASE_URL")` for environment variable
- Fallback to `config.get_main_option("sqlalchemy.url")` only for local development
- Support both sync and async URL formats (auto-convert as needed)

C. Environment-specific usage

**Local development**: Set `ALEMBIC_DATABASE_URL` or use CLI args
**CI/CD**: Always use `ALEMBIC_DATABASE_URL` environment variable
**Tests**: Use `ALEMBIC_DATABASE_URL` for Tier 2 fixtures (isolated databases)
**Production**: Use Fly.io secrets (automatically available as environment variables)

D. CI guardrails

- CI must set `ALEMBIC_DATABASE_URL` for all migration operations
- Never rely on `alembic.ini` `sqlalchemy.url` in CI
- Test migrations with both sync and async database URLs
- Validate URL resolution order in CI pipeline

E. Documentation requirements

- README must document all three URL resolution methods
- `env.example` must show examples of environment variable usage
- `alembic.ini` must have clear comments about fallback-only usage
- Charter must include this policy section
