# Database Migrations - Protectogram

## Overview

Protectogram uses Alembic for database schema management. Due to Fly.io SSH limitations (environment variables not available in SSH sessions), we've implemented HTTP-based migration endpoints.

## Migration System Architecture

### HTTP Migration Endpoints (app/api/admin/migrations.py)

All migration operations are performed via authenticated HTTP endpoints:

- `POST /api/admin/migrations/upgrade` - Apply all pending migrations
- `GET /api/admin/migrations/status` - Check current migration state
- `POST /api/admin/migrations/downgrade` - Rollback one migration
- `GET /api/admin/migrations/history` - View complete migration history

### Authentication

All endpoints require `X-Admin-Key` header with the `MIGRATION_ADMIN_KEY` secret:

```bash
curl -H "X-Admin-Key: $SECRET_KEY" https://app.fly.dev/api/admin/migrations/status
```

The `MIGRATION_ADMIN_KEY` is typically set to the same value as `SECRET_KEY`.

## Deployment Migration Process

### 1. Deploy Application First

```bash
# Staging
flyctl deploy --build-arg ENVIRONMENT=staging -a protectogram-staging

# Production
flyctl deploy --build-arg ENVIRONMENT=production -a protectogram
```

### 2. Run Migrations via HTTP

```bash
# Get your SECRET_KEY from Fly.io secrets
export SECRET_KEY=$(flyctl secrets list -a protectogram-staging | grep SECRET_KEY | awk '{print $2}')

# Apply all pending migrations
curl -X POST -H "X-Admin-Key: $SECRET_KEY" https://protectogram-staging.fly.dev/api/admin/migrations/upgrade

# Verify migration status
curl -H "X-Admin-Key: $SECRET_KEY" https://protectogram-staging.fly.dev/api/admin/migrations/status
```

### 3. Response Examples

#### Successful Migration
```json
{
  "success": true,
  "message": "Migrations completed successfully",
  "applied_migrations": ["001_initial_schema", "002_add_guardians"],
  "current_revision": "abc123def456"
}
```

#### Migration Status
```json
{
  "current_revision": "abc123def456",
  "head_revision": "abc123def456",
  "pending_migrations": [],
  "is_up_to_date": true,
  "database_url": "postgresql://...",
  "environment": "staging"
}
```

## Development Migration Process

For local development, traditional Alembic commands still work:

```bash
# Create new migration
make db-migration  # Prompts for migration message

# Apply migrations locally
make db-migrate

# Or use alembic directly
alembic revision --autogenerate -m "Add new table"
alembic upgrade head
```

## Troubleshooting

### Common Issues

1. **"Admin key required"**: Ensure `X-Admin-Key` header is set correctly
2. **"Environment variables not found"**: Verify `MIGRATION_ADMIN_KEY` secret is configured
3. **Migration fails**: Check logs with `flyctl logs -a protectogram-staging`

### Rollback Process

```bash
# Rollback one migration
curl -X POST -H "X-Admin-Key: $SECRET_KEY" https://app.fly.dev/api/admin/migrations/downgrade

# Check what was rolled back
curl -H "X-Admin-Key: $SECRET_KEY" https://app.fly.dev/api/admin/migrations/history
```

### Manual Database Access (Emergency)

If HTTP endpoints fail, you can still access the database directly:

```bash
# Connect to staging database via SSH tunnel
flyctl ssh console -a protectogram-staging
# Inside the container:
python -c "from app.database import get_sync_engine; print(get_sync_engine().url)"
```

## Implementation Details

### Alembic Configuration (alembic/env.py)

The migration system bypasses ConfigParser issues with special characters in DATABASE_URL by using direct `create_engine()`:

```python
# Lines 127-130
from sqlalchemy import create_engine
connectable = create_engine(
    database_url,
    poolclass=pool.NullPool,
)
```

### PostGIS Table Exclusion

The `include_object()` function filters out TIGER geocoder and PostGIS system tables to avoid migration conflicts.

### Security

- Admin endpoints are only accessible with valid `MIGRATION_ADMIN_KEY`
- Database operations use read-only connections where possible
- All operations are logged for audit purposes

---

**Note**: This HTTP-based migration system was implemented on 2025-09-02 to resolve SSH environment variable limitations on Fly.io deployments.
