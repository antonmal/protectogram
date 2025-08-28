# Production Deployment Guide

This document describes how to deploy Protectogram to the production environment.

## Prerequisites

- Fly.io CLI installed and authenticated
- Access to the Protectogram repository
- Production Telegram Bot Token
- Production Telnyx API credentials
- Production database credentials

## Environment Setup

### 1. Application Configuration

The production environment uses the following configuration:

```bash
# Set application environment
fly secrets set APP_ENV="prod"

# Disable debug mode for production
fly secrets set DEBUG="false"

# Set log level
fly secrets set LOG_LEVEL="INFO"
```

### 2. Database Configuration

```bash
# Set PostgreSQL connection URL (production database)
fly secrets set POSTGRES_URL="postgresql://user:password@host:port/database"
```

### 3. Telegram Configuration

```bash
# Set Telegram bot token (production bot)
fly secrets set TELEGRAM_BOT_TOKEN="your_production_bot_token"

# Set webhook secret for Telegram
fly secrets set TELEGRAM_WEBHOOK_SECRET="your_production_webhook_secret"
```

### 4. Telnyx Configuration

```bash
# Set Telnyx API key (production account)
fly secrets set TELNYX_API_KEY="your_production_telnyx_key"

# Set Telnyx connection ID
fly secrets set TELNYX_CONNECTION_ID="your_production_connection_id"
```

### 5. Access Control Configuration

```bash
# Set allowed E.164 phone numbers (comma-separated)
fly secrets set ALLOWED_E164_NUMBERS="+34722450504,+34611760244"

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

# Enable answering machine detection for production
fly secrets set FEATURE_AMD_ENABLED="true"
```

### 8. Observability

```bash
# Set Sentry DSN for error tracking
fly secrets set SENTRY_DSN="your_sentry_dsn"
```

## Deployment Process

### 1. Pre-deployment Checklist

- [ ] All tests pass locally
- [ ] Staging environment is working correctly
- [ ] Database migrations are ready
- [ ] All secrets are configured
- [ ] Monitoring is set up

### 2. Build and Deploy

```bash
# Deploy to production
fly deploy --app protectogram
```

### 3. Verify Deployment

```bash
# Check application status
fly status --app protectogram

# Check logs
fly logs --app protectogram

# Test health endpoint
curl https://protectogram.fly.dev/health/ready
```

### 4. Database Migration

```bash
# Run database migrations
fly ssh console --app protectogram
# Then run: alembic upgrade head
```

## Testing

### 1. Health Checks

- **Ready endpoint**: `GET /health/ready`
- **Live endpoint**: `GET /health/live`

### 2. Smoke Tests

```bash
# Test basic functionality
curl https://protectogram.fly.dev/health/ready
curl https://protectogram.fly.dev/admin/trigger-panic-test
```

### 3. Integration Tests

- Test Telegram bot with production credentials
- Test Telnyx webhook endpoints
- Verify call cascade functionality

## Monitoring

### 1. Application Metrics

- Monitor application logs: `fly logs --app protectogram`
- Check resource usage: `fly status --app protectogram`
- Monitor error rates via Sentry

### 2. Database Monitoring

- Monitor database connections
- Check migration status
- Monitor query performance

### 3. Business Metrics

- Monitor panic incidents
- Track call success rates
- Monitor user onboarding

## Security

### 1. Access Control

- Only authorized phone numbers can use the application
- All webhook endpoints verify signatures
- Database connections use SSL

### 2. Secrets Management

- All sensitive data stored in Fly Secrets
- No secrets in code or documentation
- Regular secret rotation recommended

### 3. Network Security

- HTTPS enforced for all endpoints
- Webhook signature verification
- Rate limiting on public endpoints

## Troubleshooting

### Common Issues

1. **Database connection errors**: Check `POSTGRES_URL` secret
2. **Telegram webhook failures**: Verify `TELEGRAM_BOT_TOKEN` and webhook URL
3. **Telnyx call failures**: Check `TELNYX_API_KEY` and connection settings
4. **Access control issues**: Verify `ALLOWED_E164_NUMBERS` configuration

### Debug Commands

```bash
# Check all secrets
fly secrets list --app protectogram

# View application logs
fly logs --app protectogram

# SSH into the application
fly ssh console --app protectogram

# Check database status
fly ssh console --app protectogram
# Then run: python -c "from app.core.database import engine; print('DB OK')"
```

## Rollback Procedure

If deployment fails:

```bash
# Rollback to previous version
fly deploy --app protectogram --image-label v1.0.0

# Or rollback to specific deployment
fly deploy --app protectogram --image-label <deployment-id>
```

## Maintenance

### 1. Regular Updates

- Monitor for security updates
- Update dependencies regularly
- Review and rotate secrets

### 2. Database Maintenance

- Monitor database size and performance
- Run regular backups
- Review and optimize queries

### 3. Application Maintenance

- Monitor error rates and performance
- Review logs for issues
- Update application as needed

## Emergency Procedures

### 1. Service Outage

1. Check application status: `fly status --app protectogram`
2. Review logs: `fly logs --app protectogram`
3. Check database connectivity
4. Verify external service status (Telegram, Telnyx)

### 2. Security Incident

1. Immediately rotate affected secrets
2. Review access logs
3. Check for unauthorized access
4. Update security measures as needed

## Performance Optimization

### 1. Resource Monitoring

- Monitor CPU and memory usage
- Check database connection pool
- Monitor external API response times

### 2. Scaling

- Monitor application load
- Scale resources as needed
- Optimize database queries

## Support

For production issues:

1. Check application logs first
2. Review monitoring dashboards
3. Contact the development team
4. Follow emergency procedures if needed
