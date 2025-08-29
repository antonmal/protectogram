# Protectogram

Protectogram is an incident management system designed to handle cascading incidents and provide real-time notifications through multiple channels including Telegram and SMS via Telnyx.

## Features

- **Health Monitoring**: Live and ready health checks with Prometheus metrics
- **Telegram Integration**: Bot for incident notifications and management
- **SMS Notifications**: Telnyx integration for SMS alerts
- **Database**: PostgreSQL with async SQLAlchemy
- **Scheduling**: APScheduler for automated tasks
- **Monitoring**: Prometheus metrics and structured logging

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL (for production)
- Telegram Bot Token (optional)
- Telnyx API Key (optional)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd protectogram
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   pip install -e ".[dev]"
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Run the development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
   ```

6. **Test the application**
   ```bash
   # Health check
   curl http://localhost:8080/health/live
   
   # Ready check
   curl http://localhost:8080/health/ready
   
   # Metrics
   curl http://localhost:8080/metrics
   ```

## Development Commands

### Code Quality

```bash
# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy .

# Security scanning
bandit -q -r app -x tests
```

### Testing

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit

# Run with coverage
pytest --cov=app tests/
```

### Docker

```bash
# Build image
docker build -t protectogram:local .

# Run container
docker run -p 8080:8080 protectogram:local
```

## Project Structure

```
app/
├── api/                    # FastAPI routers
│   ├── health.py          # Health endpoints
│   ├── metrics.py         # Prometheus metrics
│   ├── telegram.py        # Telegram webhooks
│   ├── telnyx.py          # Telnyx webhooks
│   └── admin.py           # Admin endpoints
├── core/                   # Core functionality
│   ├── settings.py        # Configuration
│   ├── logging.py         # Logging setup
│   └── flags.py           # Feature flags
├── domain/                 # Business logic
├── integrations/           # External integrations
│   ├── telegram/          # Telegram bot
│   └── telnyx/            # Telnyx client
├── scheduler/              # Background tasks
└── storage/               # Database layer
```

## API Endpoints

- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /metrics` - Prometheus metrics
- `POST /webhook/telegram` - Telegram webhook
- `POST /webhook/telnyx` - Telnyx webhook

## Deployment

### Fly.io

```bash
# Deploy to staging
fly deploy

# Deploy to production
fly deploy --config fly.prod.toml
```

### Environment Variables

Required environment variables:
- `APP_ENV`: Environment (local, staging, production)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `DATABASE_URL`: PostgreSQL connection string

Optional:
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELNYX_API_KEY`: Telnyx API key
- `TELNYX_WEBHOOK_SECRET`: Telnyx webhook secret

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Database & Migrations

### Database URLs

The application uses different database URLs for different purposes:

- **Web ORM (async)**: `APP_DATABASE_URL` - Uses `postgresql+asyncpg://` for FastAPI async operations
- **Alembic & APScheduler (sync)**: `APP_DATABASE_URL_SYNC` - Uses `postgresql+psycopg://` for migrations and job store
- **Alembic override**: `ALEMBIC_DATABASE_URL` - If set, Alembic uses this instead of `APP_DATABASE_URL_SYNC`

### Environment Variables

```bash
# Required for web app
APP_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

# Required for migrations and APScheduler
APP_DATABASE_URL_SYNC=postgresql+psycopg://user:pass@localhost/dbname

# Optional Alembic override
ALEMBIC_DATABASE_URL=postgresql+psycopg://user:pass@localhost/dbname
```

### Local Development

For local development without a local PostgreSQL installation:

1. **Integration tests** use Docker via Testcontainers (PostgreSQL 16)
2. **If Docker is unavailable**, integration tests are skipped with a clear message
3. **Migrations** can be tested using the integration test suite

### Migration Commands

```bash
# Apply all migrations
make migrate-up

# Rollback last migration
make migrate-down

# Create new migration
make migrate-revision name=add_new_table

# Test migrations (requires Docker)
make test-integration
```

### Schema

The database schema includes:

- **users**: User accounts with Telegram integration
- **member_links**: Links between watchers and travelers
- **incidents**: Incident tracking
- **alerts**: Alert notifications
- **call_attempts**: Phone call attempt tracking
- **inbox_events**: Incoming webhook events
- **outbox_messages**: Outgoing messages
- **scheduled_actions**: Scheduled tasks

All tables use `BIGSERIAL` primary keys and `TIMESTAMPTZ` timestamps with `now()` defaults.
