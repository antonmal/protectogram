# Development Environment Setup

## Security Best Practices

**⚠️ NEVER commit real secrets to git repositories!**

This guide ensures you can develop locally without compromising production security.

## Quick Start

1. **Copy environment template:**
   ```bash
   cp .env.example .env.development
   ```

2. **Fill in development-specific values** (see sections below)

3. **Start development services:**
   ```bash
   make install-dev  # Install dependencies
   make dev         # Start FastAPI + PostgreSQL + Redis
   ```

## Environment Configuration

### Database Setup
```bash
# Local PostgreSQL (recommended)
DATABASE_URL=postgresql://postgres:devpass@localhost:5432/protectogram_dev  # pragma: allowlist secret

# Or use Docker:
docker run --name protectogram-postgres -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=protectogram_dev -p 5432:5432 -d postgres:15
```

### Telegram Bot Setup

**Create a separate development bot:**

1. Message @BotFather on Telegram
2. Use `/newbot` command
3. Name it something like "ProtectogramDevBot"
4. Copy the token to `.env.development`

```bash
TELEGRAM_BOT_TOKEN=1234567890:AAE_your_dev_bot_token_here
TELEGRAM_BOT_USERNAME=ProtectogramDevBot
```

### Webhook Configuration

**For local development with ngrok:**

1. Install ngrok: `brew install ngrok` (macOS)
2. Start ngrok: `ngrok http 8000`
3. Copy the HTTPS URL to `.env.development`:

```bash
WEBHOOK_BASE_URL=https://abc123.ngrok.io
```

### Twilio Configuration

**Use Twilio test credentials for development:**

```bash
# These are safe test values from Twilio documentation
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_test_auth_token
TWILIO_FROM_NUMBER=+15005550006  # Magic test number
```

### Security Keys

**Generate secure keys for development:**

```bash
# Generate SECRET_KEY
python -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64)))"

# Generate WEBHOOK_SECRET
python -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))"
```

## Production vs Development

### ✅ Safe for Development
- Local database with dev data
- Separate Telegram bot for testing
- Twilio test credentials
- Self-signed certificates
- ngrok tunnels for webhooks

### ❌ Never Use in Development
- Production database credentials
- Production Telegram bot token (@ProtectogramBot)
- Production Twilio credentials
- Production SECRET_KEY or WEBHOOK_SECRET

## Environment Files Overview

```
.env.example          # Template (committed to git)
.env.development      # Your local dev secrets (gitignored)
.env                  # Alternative local file (gitignored)
```

**Production/Staging secrets** are managed via:
```bash
flyctl secrets set KEY=VALUE -a protectogram-staging
flyctl secrets set KEY=VALUE -a protectogram
```

## Troubleshooting

### Common Issues

1. **Database connection fails:**
   ```bash
   # Check PostgreSQL is running
   brew services start postgresql
   # Or with Docker:
   docker start protectogram-postgres
   ```

2. **Telegram webhook fails:**
   ```bash
   # Check ngrok is running and URL is correct
   curl https://your-ngrok-url.ngrok.io/health
   ```

3. **Redis connection fails:**
   ```bash
   # Start Redis locally
   brew services start redis
   # Or with Docker:
   docker run --name protectogram-redis -p 6379:6379 -d redis:7
   ```

### Development Commands

```bash
# Setup
make install-dev      # Install all dependencies
make db-setup         # Setup PostgreSQL + PostGIS
make db-migrate       # Run database migrations

# Development
make dev              # Start development server
make test             # Run tests
make lint             # Check code quality

# Database
make db-migration     # Create new migration
make db-reset         # Reset development database
```

## Security Checklist

- [ ] `.env.development` is in `.gitignore`
- [ ] Using separate dev bot token
- [ ] Using test/dev database
- [ ] Production secrets never in local files
- [ ] Generated unique keys for development

---

**Remember:** Development should be isolated from production. Never mix production secrets with development environments!
