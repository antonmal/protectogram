# Protectogram - Panic Button v1 (Telnyx Edition)

Telegram + Telnyx safety assistant for travelers and their guardians.

## Overview

Protectogram is a safety application that allows travelers to trigger panic alerts via Telegram, which then initiate a cascade of notifications to their designated guardians through both Telegram messages and phone calls with Russian TTS prompts.

## Features (Panic v1)

- **Panic Button**: Travelers can trigger panic via Telegram commands (`panic`, `тревога`, `паника`)
- **Guardian Alerts**: Immediate Telegram notifications with acknowledgment buttons
- **Call Cascade**: Automated phone calls with Russian TTS prompts
- **DTMF Acknowledgment**: Guardians can acknowledge via DTMF "1" or Telegram button
- **Idempotency**: Inbox/Outbox pattern prevents duplicate actions
- **Durable Scheduling**: APScheduler with Postgres job store for reliable reminders
- **Russian UI**: All user-facing text in Russian

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │   FastAPI App   │    │   Telnyx API    │
│                 │    │                 │    │                 │
│ • Panic Button  │◄──►│ • Webhooks      │◄──►│ • Call Control  │
│ • Acknowledgment│    │ • Domain Logic  │    │ • TTS           │
│ • Notifications │    │ • Scheduler     │    │ • DTMF          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   PostgreSQL    │
                       │                 │
                       │ • Users         │
                       │ • Incidents     │
                       │ • Alerts        │
                       │ • Call Attempts │
                       │ • Inbox/Outbox  │
                       │ • Scheduled Jobs│
                       └─────────────────┘
```

## Technology Stack

- **Backend**: FastAPI 0.111.0 (async)
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async)
- **Scheduler**: APScheduler 4.0 with Postgres job store
- **Telegram**: Aiogram 3.10.0
- **Voice**: Telnyx Call Control API
- **Deployment**: Fly.io with Docker
- **Monitoring**: Prometheus metrics + structured logging

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Fly.io CLI
- Telegram Bot Token
- Telnyx API Key

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd protectogram
   make setup
   ```

2. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your credentials
   ```

3. **Run tests**:
   ```bash
   make test
   ```

4. **Start development server**:
   ```bash
   uvicorn app.main:app --reload
   ```

### Database Setup

**No local database installation required!** Tests use Testcontainers automatically.

For local development:

1. **Set up environment**:
   ```bash
   # Copy example environment file
   cp env.example .env
   # Edit .env with your database URL
   ```

2. **Run migrations**:
   ```bash
   # Using environment variable
   ALEMBIC_DATABASE_URL="your_database_url" make db-upgrade

   # Or using CLI argument
   alembic -x db_url="your_database_url" upgrade head
   ```

3. **Reset database** (if needed):
   ```bash
   make db-reset
   ```

**Note**: For testing, no database setup is required - Testcontainers handles everything automatically.

## Deployment

### Staging Deployment

1. **Create Fly.io app**:
   ```bash
   fly apps create protectogram-staging
   ```

2. **Create Postgres database**:
   ```bash
   fly postgres create protectogram-pg-staging
   fly postgres attach protectogram-pg-staging --app protectogram-staging
   ```

3. **Set secrets**:
   ```bash
   fly secrets set \
     POSTGRES_URL="postgresql://..." \
     TELEGRAM_BOT_TOKEN="your_token" \
     TELEGRAM_WEBHOOK_SECRET="your_secret" \
     TELNYX_API_KEY="your_key" \
     TELNYX_CONNECTION_ID="your_connection" \
     APP_ENV="staging"
   ```

4. **Deploy**:
   ```bash
   make deploy-staging
   ```

5. **Configure webhooks**:
   ```bash
   # Telegram webhook
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -d "url=https://protectogram-staging.fly.dev/telegram/webhook?secret=<SECRET>"

   # Telnyx webhook (configure in Telnyx dashboard)
   ```

### Production Deployment

1. **Create production app**:
   ```bash
   fly apps create protectogram-prod
   ```

2. **Set production secrets**:
   ```bash
   fly secrets set \
     APP_ENV="prod" \
     # ... other production secrets
   ```

3. **Deploy**:
   ```bash
   make deploy-prod
   ```

## API Endpoints

### Health Checks
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /metrics` - Prometheus metrics

### Webhooks
- `POST /telegram/webhook?secret=<secret>` - Telegram updates
- `POST /telnyx/webhook` - Telnyx call events

### Admin (Staging Only)
- `POST /admin/trigger-panic-test` - Trigger test panic

## Database Schema

### Core Tables
- **users**: Telegram users with phone numbers
- **member_links**: Watcher-traveler relationships
- **incidents**: Panic incidents
- **alerts**: Notifications sent to watchers
- **call_attempts**: Individual call attempts
- **inbox_events**: Idempotency for incoming events
- **outbox_messages**: Idempotency for outgoing messages
- **scheduled_actions**: APScheduler jobs

## Monitoring

### Metrics
- `panic_incidents_started_total`
- `panic_acknowledged_total`
- `panic_canceled_total`
- `call_attempts_total{result}`
- `scheduler_job_lag_seconds`
- `telegram_messages_sent_total`

### Logs
Structured JSON logs with correlation IDs and incident tracking.

### Health Checks
- Database connectivity
- Scheduler job execution
- External API availability

## Development

### Code Quality
```bash
make lint          # Run ruff
make type-check    # Run mypy
make format        # Format code
make test          # Run all tests
```

### Database
```bash
make db-migrate    # Create migration
make db-upgrade    # Apply migrations
make db-downgrade  # Rollback migration
```

### Testing
```bash
make test-unit         # Unit tests
make test-integration  # Integration tests
make test-contract     # Contract tests
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `APP_ENV` | Environment (staging/prod) | Yes |
| `POSTGRES_URL` | Database connection | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Yes |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook secret | Yes |
| `TELNYX_API_KEY` | Telnyx API key | Yes |
| `TELNYX_CONNECTION_ID` | Telnyx connection | Yes |
| `SENTRY_DSN` | Sentry DSN | No |
| `FEATURE_PANIC` | Enable panic feature | No |

### Call Cascade Settings
- `DEFAULT_RING_TIMEOUT_SEC`: 25 seconds
- `DEFAULT_MAX_RETRIES`: 2 attempts
- `DEFAULT_RETRY_BACKOFF_SEC`: 60 seconds
- `DEFAULT_REMINDER_INTERVAL_SEC`: 120 seconds

## Troubleshooting

### Common Issues

1. **Scheduler not working**:
   - Check Postgres connection
   - Verify job store tables exist
   - Check scheduler logs

2. **Telegram webhook failing**:
   - Verify webhook URL is accessible
   - Check webhook secret
   - Ensure bot has proper permissions

3. **Telnyx calls failing**:
   - Verify API key and connection ID
   - Check webhook URL configuration
   - Ensure phone numbers are in E.164 format

### Logs
```bash
make logs  # View application logs
```

### Health Check
```bash
make health-check  # Check application health
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks: `make lint type-check test`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

---

**Protectogram v0.1.0** - Panic Button v1 (Telnyx Edition)
