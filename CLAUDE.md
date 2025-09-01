# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
make install-dev          # Install dependencies and setup development environment
make db-setup             # Setup local PostgreSQL with PostGIS
make redis-setup          # Start Redis container
make dev                  # Start full development environment (FastAPI + Celery)
make dev-stop             # Stop all development services
```

### Testing
```bash
make test                 # Run all tests with coverage
make test-unit           # Run unit tests only (marked with @pytest.mark.unit)
make test-integration    # Run integration tests (marked with @pytest.mark.integration)
make test-critical       # Run critical safety tests (marked with @pytest.mark.critical)
make test-panic          # Run panic system tests
make test-trip           # Run trip system tests
make test-suspension     # Run suspension logic tests
make test-speed          # Test panic button response time (<2s requirement)
```

### Code Quality
```bash
make lint                # Run flake8 + mypy
make format              # Format with black + isort
make security            # Run bandit + safety check
make pre-commit          # Run format + lint + critical tests
```

### Database
```bash
make db-migrate          # Apply migrations
make db-migration        # Create new migration (prompts for message)
```

## Architecture Overview

Protectogram v3.1 is a personal safety application with panic button and trip tracking functionality built on FastAPI + Celery + PostgreSQL with PostGIS.

### Critical Architecture Principles

1. **Strict Separation of Concerns**: Panic and Trip services are completely separated and never mixed
   - `app/services/panic.py` - ONLY panic alerts, trip suspension, guardian dispatch
   - `app/services/trip.py` - ONLY trip tracking, suspension-aware reminders
   - `app/services/notification.py` - Context-aware alert dispatch

2. **Suspension Logic**: When panic is triggered, all active trips are suspended immediately
   - Trip reminders STOP during panic scenarios
   - ALL trip tasks must check `trip.status != 'suspended'` before execution
   - After panic resolved, user is prompted for ETA update before resuming

3. **Task Queue Separation**: Celery tasks are separated by context
   - `app/tasks/panic_alerts.py` - Panic-related background tasks
   - `app/tasks/trip_reminders.py` - Trip reminder tasks (suspension-aware)

### Key Components

- **Settings**: Environment-specific configuration via `app/config/settings.py` with factory pattern
- **Communication**: Provider-agnostic system via `CommunicationManager` supporting Telnyx + Twilio
- **Database**: PostgreSQL with PostGIS for spatial queries, location stored as `GEOGRAPHY(POINT, 4326)`
- **Cache/Queue**: Redis for Celery broker and application cache
- **Frontend**: Telegram webhook-based bot (@ProtectogramBot prod, @ProtectogramTestBot staging)

### Performance Requirements

- **Panic Response Time**: <2 seconds from panic button to first alert dispatch
- **Voice Call Retry**: Every 3 minutes for 15 minutes with DTMF acknowledgment
- **Idempotency**: Provider event IDs and outbound operation keys prevent duplicates

### Environment Configuration

Four environments with specific configurations:
- `development` - Local PostgreSQL + Redis, ngrok webhooks, @ProtectogramDevBot
- `test` - Ephemeral DB, mocked services, `task_always_eager=True`
- `staging` - Supabase + Upstash, @ProtectogramTestBot, real Telnyx test calls
- `production` - Supabase + Upstash, @ProtectogramBot, live calls (Fly.io CDG region)

### Testing Strategy

- **Framework**: pytest + pytest-httpx (async HTTP) + pytest-asyncio (async services)
- **Critical Test Markers**: `@pytest.mark.critical` for scenarios that must always pass
- **Mocking**: All external APIs mocked with configurable failure rates
- **Key Test Scenarios**:
  - `test_panic_without_trip` - Basic panic flow
  - `test_trip_without_panic` - Basic trip with reminders
  - `test_trip_panic_resolve_sequence` - CRITICAL suspension/resume flow
  - `test_panic_during_trip_overdue` - Panic while trip already overdue

### Multi-language Support

- Primary: Russian (ru)
- Secondary: English (en), Spanish (es)
- Context-aware templates for panic vs trip_reminder vs trip_overdue scenarios

## Deployment

- **Staging**: `make deploy-staging` (uses `fly.staging.toml`)
- **Production**: `make deploy-prod` (uses `fly.toml`)
- **Monitoring**: `fly logs --app protectogram-{env}`, `make monitor` (Celery Flower)

## Required Environment Variables

Development requires `.env.development` with:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string  
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` - Twilio credentials

See `app/config/settings.py` for complete environment variable reference.