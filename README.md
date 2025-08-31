# Protectogram

Incident Management System

## Features

- FastAPI-based web application
- Structured JSON logging with correlation IDs
- Health and metrics endpoints
- APScheduler for background tasks
- PostgreSQL database with Alembic migrations
- Testcontainers for integration testing

## Development Prerequisites

### Required Software

- **Python 3.12+**
- **Docker Desktop** (macOS/Windows) or **Colima** (macOS) - for integration tests
- **Git**

### Docker Setup

1. **Start Docker:**
   ```bash
   # macOS with Docker Desktop
   open -a Docker
   
   # macOS with Colima
   colima start
   ```

2. **Pre-pull Postgres image** (recommended for slow networks):
   ```bash
   docker pull postgres:16
   ```

## Development Setup

1. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

## Testing

- **Unit tests:** `pytest tests/unit/`
- **Integration tests:** `pytest tests/integration/` (requires Docker)
- **Contract tests:** `pytest tests/contract/`
- **All tests:** `pytest`

## Health & Metrics

- **Health check:** `GET /health/live` - Returns 200 if process is alive
- **Readiness check:** `GET /health/ready` - Returns 200 if database and scheduler are healthy
- **Metrics:** `GET /metrics` - Prometheus metrics in text format

## Scheduler & Readiness

The application includes an APScheduler-based task scheduler that:

- Uses SQLAlchemyJobStore for persistence on `APP_DATABASE_URL_SYNC`
- Runs a heartbeat job every minute to monitor scheduler health
- Provides clean startup/shutdown hooks via FastAPI lifespan
- Can be disabled by setting `SCHEDULER_ENABLED=false`

### Environment Variables

- `SCHEDULER_ENABLED` - Enable/disable scheduler (default: false)
- `SCHEDULER_JOBSTORE_TABLE_NAME` - Job store table name (default: "apscheduler_jobs")
- `STARTUP_HEARTBEAT_JOB_CRON` - Heartbeat job schedule (default: "*/1 * * * *")
- `READINESS_DB_TIMEOUT_SEC` - Database timeout for readiness checks (default: 3)

## Telegram Webhook & Outbox

### Webhook Setup

To set up Telegram webhook in staging:

1. **Configure environment variables:**
   ```bash
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_WEBHOOK_SECRET=your_webhook_secret
   TELEGRAM_API_BASE=https://api.telegram.org
   TELEGRAM_ALLOWLIST_CHAT_IDS=1111,2222  # Optional: restrict to specific chat IDs
   ```

2. **Set webhook URL in Telegram:**
   ```bash
   curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://<your-app-domain>/telegram/webhook",
       "secret_token": "<TELEGRAM_WEBHOOK_SECRET>"
     }'
   ```

### Deduplication & Idempotency

#### Inbox Deduplication
- **Provider Event ID**: Unique identifier for each Telegram update
  - For messages: `str(update.update_id)`
  - For callback queries: `callback_query.id`
- **Database**: `inbox_events` table with `UNIQUE(provider, provider_event_id)`
- **Behavior**: Duplicate events are logged and dropped with 200 response

#### Outbox Idempotency
- **Idempotency Key**: Generated as `telegram:{chat_id}:{hash(text)}`
- **Database**: `outbox_messages` table with `UNIQUE(idempotency_key)`
- **Behavior**: 
  - First call: Insert pending record, send message, update with `provider_message_id`
  - Duplicate call: Return existing `provider_message_id` without network call

### Supported Commands

- `/start` → Replies with "👋 Привет! Бот подключен."
- `/ping` → Replies with "pong"
- Callback queries → Answers with acknowledgment and sends "✅ Клик получен."

### Staging Allowlist

During staging, use `TELEGRAM_ALLOWLIST_CHAT_IDS` to restrict bot access to specific chat IDs:
```bash
TELEGRAM_ALLOWLIST_CHAT_IDS=1111,2222,3333
```

Messages from non-allowed chats are ignored with a log entry but return 200 to Telegram.

### Monitoring

The following Prometheus metrics are available:
- `inbound_events_total{provider="telegram",type}` - Inbound events by type
- `duplicate_inbox_dropped_total{provider="telegram"}` - Duplicate events dropped
- `outbox_sent_total{channel="telegram"}` - Messages sent successfully
- `outbox_errors_total{channel="telegram"}` - Send errors

### Security

- **Webhook Secret**: Required `X-Telegram-Bot-Api-Secret-Token` header validation
- **No Query Parameters**: Secret is never accepted in URL parameters
- **Allowlist**: Optional chat ID restriction for staging environments

## Local tests with Testcontainers

### Prerequisites

- **Docker**: Must be running locally for integration and contract tests
- **No local Postgres required**: All database tests use ephemeral containers

### Test Setup

The test suite automatically provisions PostgreSQL 16 containers for integration and contract tests:

- **Session-level container**: Started once per test session with automatic migration application
- **Environment variables**: Auto-set by `tests/integration/conftest.py`
- **Database URLs**: 
  - `APP_DATABASE_URL` (async) for web app
  - `APP_DATABASE_URL_SYNC` (sync) for Alembic and APScheduler
  - `ALEMBIC_DATABASE_URL` (sync) for migrations

### Running Tests

```bash
# Unit tests (no database required)
pytest -q tests/unit --import-mode=importlib

# Integration tests (requires Docker)
pytest -q tests/integration --import-mode=importlib

# Contract tests (requires Docker)
pytest -q tests/contract --import-mode=importlib

# All tests
pytest --import-mode=importlib
```

### Docker Unavailable

If Docker is not available, integration and contract tests are automatically skipped with a clear message:

```
SKIPPED [1] tests/integration/test_migrations.py::test_migrations_head_applied
Docker/Testcontainers not available
```

### CI Configuration

GitHub Actions example with Docker support:

```yaml
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip wheel
          pip install -r requirements.txt -c constraints.txt
      - name: Pre-pull Postgres image
        run: docker pull postgres:16
      - name: Run tests
        env:
          PYTEST_DISABLE_PLUGIN_AUTOLOAD: "1"
        run: |
          pytest -q tests/unit --import-mode=importlib
          pytest -q tests/integration --import-mode=importlib
          pytest -q tests/contract --import-mode=importlib
```

### Test Architecture

- **Unit tests**: Pure logic tests, no database required
- **Integration tests**: Use Testcontainers PostgreSQL, test database interactions
- **Contract tests**: Use Testcontainers PostgreSQL, test API contracts with real database
- **Session fixtures**: Database container started once per test session
- **Migration application**: Automatic `alembic upgrade head` on container startup
