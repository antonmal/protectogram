# Staging Deployment Guide

This document describes how to deploy Protectogram to the staging environment.

## Prerequisites

- Fly.io CLI installed and authenticated
- Access to the Protectogram repository
- Telegram Bot Token (for staging)
- Telnyx API credentials (for staging)

## Environment Setup

### 1. Application Configuration

The staging environment uses the following configuration:

```bash
# Set application environment
fly secrets set APP_ENV="staging"

# Enable debug mode for staging
fly secrets set DEBUG="true"

# Set log level
fly secrets set LOG_LEVEL="DEBUG"
```

### 2. Database Configuration

```bash
# Set PostgreSQL connection URL
fly secrets set POSTGRES_URL="postgresql://user:password@host:port/database"
```

### 3. Telegram Configuration

```bash
# Set Telegram bot token (staging bot)
fly secrets set TELEGRAM_BOT_TOKEN="your_staging_bot_token"

# Set webhook secret for Telegram
fly secrets set TELEGRAM_WEBHOOK_SECRET="your_webhook_secret"
```

### 4. Telnyx Configuration

```bash
# Set Telnyx API key (staging account)
fly secrets set TELNYX_API_KEY="your_staging_telnyx_key"

# Set Telnyx connection ID
fly secrets set TELNYX_CONNECTION_ID="your_staging_connection_id"
```

### 5. Access Control Configuration

```bash
# Set allowed E.164 phone numbers (comma-separated)
fly secrets set ALLOWED_E164_NUMBERS="+1234567890,+0987654321"

# Enable access control
fly secrets set FEATURE_ALLOW_ONLY_WHITELIST="true"
```

### 6. Feature Flags

```bash
# Enable panic feature
fly secrets set FEATURE_PANIC="true"

# Enable scheduler
fly secrets set SCHEDULER_ENABLED="true"

# Enable database connections
fly secrets set ENABLE_DB="true"
```

### 7. Call Cascade Settings

```bash
# Set call timing parameters
fly secrets set PANIC_RETRY_INTERVAL_SEC="120"
fly secrets set CALL_RING_TIMEOUT_SEC="25"
fly secrets set CALL_MAX_RETRIES="2"
fly secrets set INCIDENT_MAX_TOTAL_RING_SEC="180"

# Disable answering machine detection for staging
fly secrets set FEATURE_AMD_ENABLED="false"
```

## Deployment Process

### 1. Build and Deploy

```bash
# Deploy to staging
fly deploy --app protectogram-staging
```

### 2. Verify Deployment

```bash
# Check application status
fly status --app protectogram-staging

# Check logs
fly logs --app protectogram-staging

# Test health endpoint
curl https://protectogram-staging.fly.dev/health/ready
```

### 3. Database Migration

```bash
# Run database migrations
fly ssh console --app protectogram-staging
# Then run: alembic upgrade head
```

## Testing

### 1. Health Checks

- **Ready endpoint**: `GET /health/ready`
- **Live endpoint**: `GET /health/live`

### 2. Telegram Bot

- Send `/start` to the staging bot
- Test onboarding flow
- Test panic button functionality

### 3. Telnyx Integration

- Test webhook endpoints
- Verify call cascade functionality

## Monitoring

### 1. Application Metrics

- Monitor application logs: `fly logs --app protectogram-staging`
- Check resource usage: `fly status --app protectogram-staging`

### 2. Database Monitoring

- Monitor database connections
- Check migration status

## Troubleshooting

### Common Issues

1. **Database connection errors**: Check `POSTGRES_URL` secret
2. **Telegram webhook failures**: Verify `TELEGRAM_BOT_TOKEN` and webhook URL
3. **Telnyx call failures**: Check `TELNYX_API_KEY` and connection settings

### Debug Commands

```bash
# Check all secrets
fly secrets list --app protectogram-staging

# View application logs
fly logs --app protectogram-staging

# SSH into the application
fly ssh console --app protectogram-staging
```

## Security Notes

- All sensitive configuration is stored in Fly Secrets
- Access control is enabled for staging
- Debug mode is enabled for troubleshooting
- Database connections use SSL
- Webhook endpoints verify signatures

## Next Steps

After successful staging deployment:

1. Run full test suite
2. Verify all integrations work
3. Test panic functionality end-to-end
4. Prepare for production deployment
