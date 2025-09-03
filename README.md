# Protectogram v3.1

Personal safety application with panic button and trip tracking functionality built on FastAPI + PostgreSQL + Redis.

## Quick Start

### Deployment (Production/Staging)

#### New Migration Process (2025-09-02)
**IMPORTANT:** SSH-based migrations no longer work due to environment variables not being available in SSH sessions.

1. **Deploy application with explicit environment:**
   ```bash
   # Staging
   flyctl deploy --build-arg ENVIRONMENT=staging -a protectogram-staging

   # Production
   flyctl deploy --build-arg ENVIRONMENT=production -a protectogram
   ```

2. **Run migrations via HTTP endpoints:**
   ```bash
   # Get your SECRET_KEY from secrets
   export SECRET_KEY=$(flyctl secrets list -a protectogram-staging | grep SECRET_KEY | awk '{print $2}')

   # Apply migrations
   curl -H "X-Admin-Key: $SECRET_KEY" https://protectogram-staging.fly.dev/api/admin/migrations/upgrade

   # Check status
   curl -H "X-Admin-Key: $SECRET_KEY" https://protectogram-staging.fly.dev/api/admin/migrations/status
   ```

#### Migration Endpoints
- `POST /api/admin/migrations/upgrade` - Apply pending migrations
- `GET /api/admin/migrations/status` - Check current migration state
- `POST /api/admin/migrations/downgrade` - Rollback one migration
- `GET /api/admin/migrations/history` - View migration history

### Development

See `CLAUDE.md` for comprehensive development commands and architecture overview.

```bash
make install-dev     # Setup development environment
make dev            # Start FastAPI + Celery + Redis
make test           # Run tests with coverage
```

## Architecture

- **Backend:** FastAPI with async SQLAlchemy + PostgreSQL (PostGIS)
- **Queue:** Celery with Redis broker
- **Deployment:** Fly.io with Docker
- **Frontend:** Telegram bot integration
- **Database:** Supabase (staging/production), local PostgreSQL (development)

## Critical Features

- **Panic Button:** <2 second response time requirement
- **Trip Tracking:** Location-based safety with automatic alerts
- **Guardian System:** Multi-level emergency contact hierarchy
- **Suspension Logic:** Trip alerts stop during panic scenarios
- **Multi-language:** Russian, English, Spanish support

## Environment Variables

Required secrets (set with `flyctl secrets set KEY=VALUE`):
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` - Communication provider
- `SECRET_KEY` - Application security key
- `WEBHOOK_SECRET` - Webhook validation key
- `MIGRATION_ADMIN_KEY` - Migration endpoint authentication (typically same as SECRET_KEY)

## Recent Major Changes (2025-09-02)

- **Fixed environment configuration** - staging was incorrectly running in development mode
- **Implemented HTTP migration system** - bypasses SSH limitations
- **Fixed phone number validation** - now accepts real-world formats with brackets/spaces/dashes
- **Updated build process** - requires explicit `--build-arg ENVIRONMENT=staging`

Fresh start on 2025-08-31.
