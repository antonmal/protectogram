# Deployment Guide - Protectogram

## Overview

Protectogram deploys to Fly.io with Docker containerization. This guide covers the updated deployment process with critical changes made on 2025-09-02.

## Critical Changes (2025-09-02)

### Build Process Requirements

1. **Explicit Environment Arguments Required**
   - Fly.io build args from `fly.staging.toml` are not automatically passed
   - Must specify environment explicitly: `--build-arg ENVIRONMENT=staging`

2. **Dockerfile Environment Handling Fixed**
   - **Before**: `ARG ENV=prod` (hardcoded)
   - **After**: `ARG ENVIRONMENT=production` → `ENV ENVIRONMENT=${ENVIRONMENT}` (dynamic)

3. **SSH Migration Limitations**
   - SSH sessions don't have environment variables
   - Migration must be done via HTTP endpoints (see `docs/migrations.md`)

## Deployment Process

### 1. Build and Deploy

#### Staging Deployment
```bash
# Deploy with explicit environment
flyctl deploy --build-arg ENVIRONMENT=staging -a protectogram-staging

# Verify deployment
flyctl logs -a protectogram-staging --region cdg --no-tail | tail -10
```

#### Production Deployment
```bash
# Deploy with explicit environment
flyctl deploy --build-arg ENVIRONMENT=production -a protectogram

# Verify deployment
flyctl logs -a protectogram --region cdg --no-tail | tail -10
```

### 2. Run Migrations

**IMPORTANT**: Migrations must be run via HTTP endpoints, not SSH.

```bash
# Get admin key (typically same as SECRET_KEY)
export ADMIN_KEY=$(flyctl secrets list -a protectogram-staging | grep SECRET_KEY | awk '{print $2}')

# Apply migrations
curl -X POST -H "X-Admin-Key: $ADMIN_KEY" https://protectogram-staging.fly.dev/api/admin/migrations/upgrade

# Verify migration status
curl -H "X-Admin-Key: $ADMIN_KEY" https://protectogram-staging.fly.dev/api/admin/migrations/status
```

### 3. Verification

```bash
# Check health endpoint
curl https://protectogram-staging.fly.dev/health

# Monitor logs for errors
flyctl logs -a protectogram-staging --region cdg

# Test Telegram bot functionality
# Send /start to @ProtectogramTestBot (staging) or @ProtectogramBot (production)
```

## Configuration Files

### fly.staging.toml
```toml
app = "protectogram-staging"
primary_region = "cdg"

[build]
  args = { ENVIRONMENT = "staging" }  # This syntax is correct but args not auto-passed

[env]
  PORT = "8000"

# ... rest of configuration
```

### fly.toml (Production)
```toml
app = "protectogram"
primary_region = "cdg"

[build]
  args = { ENVIRONMENT = "production" }

[env]
  PORT = "8000"

# ... rest of configuration
```

### Dockerfile Environment Handling
```dockerfile
# Dynamic environment handling (FIXED)
ARG ENVIRONMENT=production
ENV ENVIRONMENT=${ENVIRONMENT}

# App configuration based on environment
RUN if [ "$ENVIRONMENT" = "development" ]; then \
      echo "Development environment detected"; \
    elif [ "$ENVIRONMENT" = "staging" ]; then \
      echo "Staging environment detected"; \
    else \
      echo "Production environment detected"; \
    fi
```

## Environment-Specific Settings

### Staging Environment
- **App**: `protectogram-staging`
- **Database**: Supabase staging instance
- **Redis**: Upstash staging
- **Telegram Bot**: @ProtectogramTestBot
- **Region**: CDG (Paris)

### Production Environment
- **App**: `protectogram`
- **Database**: Supabase production instance
- **Redis**: Upstash production
- **Telegram Bot**: @ProtectogramBot
- **Region**: CDG (Paris)

## Required Secrets

Set via `flyctl secrets set KEY=VALUE -a app-name`:

### Core Application
- `DATABASE_URL` - PostgreSQL connection string (Supabase)
- `REDIS_URL` - Redis connection string (Upstash)
- `SECRET_KEY` - Application security key
- `WEBHOOK_SECRET` - Webhook validation key

### External Services
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `TWILIO_ACCOUNT_SID` - Twilio account identifier
- `TWILIO_AUTH_TOKEN` - Twilio authentication token
- `TWILIO_FROM_NUMBER` - Twilio phone number for calls/SMS

### Optional
- `SENTRY_DSN` - Error tracking (optional)
- `MIGRATION_ADMIN_KEY` - Migration endpoint auth (defaults to SECRET_KEY)

## Troubleshooting

### Common Issues

1. **"relation 'users' does not exist"**
   - App deployed with wrong environment (development vs staging)
   - Solution: Redeploy with correct `--build-arg ENVIRONMENT=staging`

2. **Build args not working**
   - Fly.io doesn't auto-pass build args from .toml files
   - Solution: Always use explicit `--build-arg ENVIRONMENT=staging`

3. **Migration failures**
   - SSH doesn't have environment variables
   - Solution: Use HTTP migration endpoints (see `docs/migrations.md`)

4. **Phone validation errors**
   - Fixed 2025-09-02: Now accepts formats like "(555) 123-4567"
   - Field validators normalize input automatically

### Diagnostic Commands

```bash
# Check current environment in running app
flyctl ssh console -a protectogram-staging
python -c "import os; print('Environment:', os.getenv('ENVIRONMENT', 'NOT_SET'))"

# View recent logs
flyctl logs -a protectogram-staging --region cdg --no-tail | tail -50

# Check secrets configuration
flyctl secrets list -a protectogram-staging

# Test database connectivity
curl -H "X-Admin-Key: $ADMIN_KEY" https://app.fly.dev/api/admin/migrations/status
```

## Legacy Commands

Previous Makefile commands still work for reference:

```bash
make deploy-staging  # Uses fly.staging.toml
make deploy-prod     # Uses fly.toml
make monitor         # Celery Flower monitoring
```

However, these may not pass the required build arguments correctly.

---

**Last Updated**: 2025-09-02 - Major deployment process overhaul
