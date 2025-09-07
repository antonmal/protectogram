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

### Panic Button Testing Scripts (2025-09-03)
```bash
# Real Twilio Integration Tests (requires ngrok + Twilio credentials)
python test_panic_twilio.py          # Full DTMF test with real voice calls
python test_simple_panic.py          # Direct Twilio provider test
python test_panic_local.py           # Local service testing (mocked Twilio)

# Database Cleanup Utilities
python cleanup_panic_alerts.py       # Clean panic alerts only
python cleanup_all_test_data.py      # Clean all test guardians and relationships
```

**Testing Flow**: Start server → run ngrok → set WEBHOOK_BASE_URL → run test → answer call → press 1 or 9 → verify acknowledgment

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

1. **Panic Button System**: Fully implemented with Twilio integration (2025-09-03)
   - **Voice calls with DTMF**: Users press 1=positive acknowledgment, 9=false alarm
   - **Cascade notifications**: Voice call → wait 30s → SMS backup → repeat every 60s
   - **Real-time webhooks**: Twilio callbacks process DTMF and update alert status
   - **Service**: `app/services/panic_service.py` - Complete panic alert management
   - **Provider**: `app/providers/twilio_provider.py` - Real Twilio voice/SMS integration
   - **Webhooks**: `app/api/webhooks/twilio.py` - DTMF processing endpoints

2. **Communication Architecture**: Provider-agnostic system with working Twilio implementation
   - **Core**: `app/core/communications.py` - Abstract communication interfaces
   - **TwiML Generation**: Absolute URLs required for DTMF callbacks to work
   - **Acknowledgment Flow**: Database updates on DTMF → TwiML response → call completion

3. **Suspension Logic**: When panic is triggered, all active trips are suspended immediately
   - Trip reminders STOP during panic scenarios
   - ALL trip tasks must check `trip.status != 'suspended'` before execution
   - After panic resolved, user is prompted for ETA update before resuming

4. **Task Queue Separation**: Background processing via asyncio (Celery integration pending)
   - **Cascade Logic**: Async background tasks handle notification timing
   - **Database Transactions**: Proper session handling to prevent rollback conflicts

### Key Components

- **Settings**: Environment-specific configuration via `app/config/settings.py` with factory pattern
- **Communication**: Working Twilio integration with DTMF support, provider-agnostic design for future expansion
- **Database**: PostgreSQL with panic alert models, notification attempt tracking, proper foreign key relationships
- **Panic Models**: `app/models/panic.py` - PanicAlert and PanicNotificationAttempt with CASCADE deletes
- **Cache/Queue**: Redis for future Celery integration (currently using asyncio background tasks)
- **Frontend**: FastAPI REST endpoints + Twilio webhooks (Telegram bot integration pending)

### Performance Requirements

- **Panic Response Time**: ✅ ACHIEVED - ~1 second from API call to Twilio voice call initiation
- **DTMF Acknowledgment**: ✅ WORKING - Press 1/9 during call for immediate acknowledgment
- **Cascade Timing**: Voice call → 30s wait → SMS backup → 60s repeat cycle for 15 minutes
- **Webhook Processing**: Real-time DTMF handling with proper TwiML responses
- **Idempotency**: Provider event IDs prevent duplicate processing

### Environment Configuration

Four environments with specific configurations:
- `development` - ✅ WORKING - Local PostgreSQL, ngrok webhooks (https://08c079e98aea.ngrok-free.app), real Twilio calls
- `test` - Ephemeral DB, mocked services, `task_always_eager=True`
- `staging` - Supabase + Upstash, @ProtectogramTestBot, ready for Twilio staging testing
- `production` - Supabase + Upstash, @ProtectogramBot, production Twilio calls (Fly.io CDG region)

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

### Critical Deployment Changes (2025-09-02)

**IMPORTANT: SSH-based migrations no longer work** - environment variables not available in SSH sessions.

#### New Migration Process
1. **Deploy application first**: `flyctl deploy --build-arg ENVIRONMENT=staging -a protectogram-staging`
2. **Run migrations via HTTP**: `curl -H "X-Admin-Key: $SECRET_KEY" https://protectogram-staging.fly.dev/api/admin/migrations/upgrade`
3. **Verify**: Check migration status: `curl -H "X-Admin-Key: $SECRET_KEY" https://app/api/admin/migrations/status`

#### Build Process Requirements
- **Must specify environment explicitly**: `--build-arg ENVIRONMENT=staging`
- **Dockerfile fixed**: `ARG ENVIRONMENT=production` → `ENV ENVIRONMENT=${ENVIRONMENT}`
- **fly.staging.toml syntax**: `args = { ENVIRONMENT = "staging" }`

#### Migration Endpoints (app/api/admin/migrations.py)
- `POST /api/admin/migrations/upgrade` - Apply pending migrations
- `GET /api/admin/migrations/status` - Check current migration state
- `POST /api/admin/migrations/downgrade` - Rollback one migration
- `GET /api/admin/migrations/history` - View migration history
- **Authentication**: Requires `X-Admin-Key` header with `MIGRATION_ADMIN_KEY` (same as `SECRET_KEY`)

#### Phone Number Validation Fixed
- **Problem**: Regex `^\+[1-9]\d{1,14}$` rejected real-world formats like "(555) 123-4567"
- **Solution**: Field validators in `app/schemas/user.py` and `app/schemas/guardian.py` normalize input
- **Supports**: Brackets, spaces, dashes automatically removed and `+` country code ensured

## Critical Bug Fixes & Solutions (2025-09-03)

### DTMF Not Working - Multiple Critical Issues

#### Issue 1: Relative TwiML Action URLs
- **Problem**: TwiML `<Gather>` used relative action="/webhooks/twilio/voice"
- **Symptom**: DTMF digits not sent back to webhook, user hears "Invalid input" loop
- **Solution**: Use absolute URLs in TwiML: `action="https://08c079e98aea.ngrok-free.app/webhooks/twilio/voice"`
- **Location**: `app/api/webhooks/twilio.py:224` - `_twiml_gather()` function

#### Issue 2: Database Schema Constraint
- **Problem**: Status column VARCHAR(20) too small for "acknowledged_positive" (21 chars)
- **Symptom**: "Sorry, error processing your response" due to database constraint violation
- **Solution**: Increase to VARCHAR(30), create migration
- **Files**: `app/models/panic.py:114`, migration `d7c995e2a3b4`

#### Issue 3: Multiple Rows Query Error
- **Problem**: `scalar_one_or_none()` failed when multiple attempts had same CallSid
- **Symptom**: "Multiple rows found when one or none was required" → webhook error
- **Solution**: Use `.order_by().first()` to get latest attempt instead
- **Location**: `app/api/webhooks/twilio.py:38-44` and `app/api/webhooks/twilio.py:139-143`

### Database Transaction Issues
- **Problem**: Session rollbacks during notification attempt saves in background tasks
- **Symptom**: "Method 'commit()' can't be called here; method '_prepare_impl()' is already in progress"
- **Root Cause**: Multiple async tasks trying to commit simultaneously
- **Solution**: Proper session handling and error recovery in cascade notifications

### Testing & Development Issues
- **Problem**: Test data accumulation causing UUID conflicts and state pollution
- **Solution**: Automatic cleanup in test scripts, proper test data isolation
- **Files**: Enhanced `test_panic_twilio.py` with `cleanup_existing_test_data()`

### Legacy Commands (for reference)
- **Staging**: `make deploy-staging` (uses `fly.staging.toml`)
- **Production**: `make deploy-prod` (uses `fly.toml`)
- **Monitoring**: `fly logs --app protectogram-{env}`, `make monitor` (Celery Flower)

## Required Environment Variables

### Development Environment (`.env.development`)
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/protectogram_dev  # pragma: allowlist secret

# Twilio (REQUIRED for panic button)
TWILIO_ACCOUNT_SID=ACxxxxx          # Twilio Account SID  # pragma: allowlist secret
TWILIO_AUTH_TOKEN=xxxxxx            # Twilio Auth Token  # pragma: allowlist secret
TWILIO_FROM_NUMBER=+1234567890      # Verified Twilio phone number
WEBHOOK_BASE_URL=https://08c079e98aea.ngrok-free.app  # ngrok tunnel URL

# Optional
REDIS_URL=redis://localhost:6379
TELEGRAM_BOT_TOKEN=1234:AAA         # For future Telegram integration
```

### Staging/Production Additional Variables
```bash
# Panic Button
ENVIRONMENT=staging                 # or production
SECRET_KEY=xxx                     # For admin endpoints

# Database (Supabase example)
DATABASE_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres  # pragma: allowlist secret

# Webhooks
WEBHOOK_BASE_URL=https://protectogram-staging.fly.dev
```

**⚠️ Critical**: `WEBHOOK_BASE_URL` must be absolute URL for DTMF to work. Twilio requires absolute action URLs in TwiML.

See `app/config/settings.py` for complete environment variable reference.
- to memorize The region used on Fly.io is CDG.
- to memorize Use the staging db endpoint to clear the test data from db as soon as you deploy to staging. (curl -X DELETE "https://protectogram-staging.fly.dev/api/admin/database/clear-test-data"...)
