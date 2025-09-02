# Staging Deployment Guide

## Overview

This guide covers deploying Protectogram to the staging environment using Fly.io.

## Prerequisites

1. **Fly.io CLI installed** - `brew install flyctl` (macOS)
2. **Authenticated with Fly.io** - `flyctl auth login`
3. **Staging app created** - App name: `protectogram-staging`

## Staging Environment Configuration

### Required Environment Variables

Set these secrets using: `flyctl secrets set -a protectogram-staging KEY=VALUE`

#### Database & Cache
```bash
DATABASE_URL=postgresql+asyncpg://[staging_db_url]
REDIS_URL=redis://[staging_redis_url]
```

#### Telegram Bot
```bash
TELEGRAM_BOT_TOKEN=[staging_bot_token]  # @ProtectogramStagingBot
TELEGRAM_BOT_USERNAME=@ProtectogramStagingBot
WEBHOOK_BASE_URL=https://protectogram-staging.fly.dev
```

#### Security
```bash
SECRET_KEY=[random_32_char_string]
WEBHOOK_SECRET=[random_webhook_secret]
```

#### Twilio (Test Account)
```bash
TWILIO_ACCOUNT_SID=[staging_account_sid]
TWILIO_AUTH_TOKEN=[staging_auth_token]
TWILIO_FROM_NUMBER=[test_phone_number]
```

#### Optional
```bash
SENTRY_DSN=[staging_sentry_dsn]  # Optional monitoring
```

## Deployment Steps

### 1. Build and Deploy
```bash
# Deploy to staging
flyctl deploy -a protectogram-staging --config fly.staging.toml

# Check deployment status
flyctl status -a protectogram-staging

# View logs
flyctl logs -a protectogram-staging
```

### 2. Database Migration
```bash
# Connect to staging app
flyctl ssh console -a protectogram-staging

# Run migrations
cd /app && python -m alembic upgrade head

# Exit SSH session
exit
```

### 3. Set Telegram Webhook
```bash
# Set webhook URL for staging bot
curl -X POST "https://protectogram-staging.fly.dev/webhooks/telegram/set-webhook" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://protectogram-staging.fly.dev/webhooks/telegram/webhook"}'
```

### 4. Health Checks
```bash
# Check application health
curl https://protectogram-staging.fly.dev/health

# Check bot health
curl https://protectogram-staging.fly.dev/webhooks/telegram/health

# Test database connection
curl -X POST https://protectogram-staging.fly.dev/webhooks/telegram/test-database
```

## Testing the Staging Environment

### 1. Telegram Bot Testing
1. Find `@ProtectogramStagingBot` on Telegram
2. Send `/start` command
3. Complete registration flow:
   - Share phone contact
   - Select gender
   - Select language
4. Test guardian functionality:
   - Go to guardians menu
   - Add a guardian
   - Verify guardian appears in list

### 2. API Testing
```bash
# Test user registration via API
curl -X POST "https://protectogram-staging.fly.dev/api/v1/users" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "phone_number": "+34666000123",
    "preferred_language": "en",
    "gender": "other"
  }'
```

## Monitoring and Debugging

### View Logs
```bash
# Real-time logs
flyctl logs -a protectogram-staging -f

# Specific time range
flyctl logs -a protectogram-staging --since 1h
```

### SSH Access
```bash
# Connect to staging app
flyctl ssh console -a protectogram-staging

# Check running processes
ps aux

# Check environment variables
env | grep ENVIRONMENT
```

### Common Issues

#### Bot Not Responding
1. Check bot token is valid: `/webhooks/telegram/health`
2. Verify webhook is set correctly
3. Check logs for initialization errors

#### Database Errors
1. Verify DATABASE_URL is correct
2. Run diagnostic endpoint: `/webhooks/telegram/test-database`
3. Check if migrations are applied

#### Registration Failures
1. Check if all required fields are provided
2. Verify phone number format (+international)
3. Check logs for validation errors

## Staging vs Production Differences

| Aspect | Staging | Production |
|--------|---------|------------|
| VM Size | 512MB, shared CPU | 1GB+, dedicated CPU |
| Auto-scaling | Min 0, max 2 | Min 1, max N |
| Database | Staging DB | Production DB |
| Bot Account | @ProtectogramStagingBot | @ProtectogramBot |
| Twilio | Test account | Live account |
| Monitoring | Optional Sentry | Full monitoring |

## Rollback Process

If deployment fails:
```bash
# List recent releases
flyctl releases -a protectogram-staging

# Rollback to previous version
flyctl releases rollback [RELEASE_ID] -a protectogram-staging
```

## Next Steps After Staging

1. **Complete testing** - Verify all features work
2. **Load testing** - Test with multiple concurrent users
3. **Guardian notification testing** - Verify emergency flows
4. **Security review** - Check all endpoints are secure
5. **Performance optimization** - Monitor response times
6. **Production deployment** - Deploy to production environment
