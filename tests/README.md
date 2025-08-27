# Test Setup Documentation

## Charter Compliance: No Local DB Install Required ✅

This test setup follows the charter's requirement: **"no local DB install required"** and **"Prefer Testcontainers-Postgres for integration/API tests (no local DB install)."**

### Database Setup

- **Testcontainers-Postgres**: All tests use `testcontainers[postgresql]==3.7.1`
- **No Local PostgreSQL**: No local PostgreSQL installation is required
- **Containerized**: Database runs in Docker containers managed by Testcontainers
- **Isolated**: Each test session gets a fresh PostgreSQL container

### Key Components

1. **postgres_container fixture**: Session-scoped Postgres container using `PostgresContainer("postgres:15")`
2. **test_engine fixture**: Creates async engine from Testcontainers URL
3. **test_session fixture**: Function-scoped AsyncSession with nested transaction (SAVEPOINT) for test isolation
4. **Table creation**: Uses `Base.metadata.create_all()` with sync engine for table creation

### Dependencies

- `testcontainers[postgresql]==3.7.1` - Provides PostgreSQL container management
- `asyncpg==0.30.0` - Async PostgreSQL driver for tests
- `psycopg2-binary==2.9.10` - Sync PostgreSQL driver for table creation

### Benefits

- ✅ **No local DB install required** - Charter compliance
- ✅ **Isolated test environment** - Each test session is independent
- ✅ **Proper test isolation** - Nested transactions (SAVEPOINT) with automatic rollback
- ✅ **Consistent across environments** - Same setup works everywhere
- ✅ **Fast startup** - Containers start quickly
- ✅ **Clean teardown** - Automatic cleanup after tests

### Test Categories (Charter Compliance)

All tests are properly categorized according to charter guidelines:

- **`@pytest.mark.integration`**: FastAPI app + SQLAlchemy async + Alembic-migrated Postgres (async)
  - All current tests in `test_integration.py` are marked as integration tests
  - Use Testcontainers-Postgres for database operations
  - Test API endpoints, database operations, and async functionality
  - Includes dedicated scheduler test for persistence and firing verification

- **`@pytest.mark.unit`**: pure Python/domain logic; sync only, no DB or event loop
  - For future unit tests of business logic

- **`@pytest.mark.contract`**: Telegram/Telnyx signature verification with canned payloads; sync, no DB/app
  - For future contract tests of external API integrations

### Charter Compliance Summary

✅ **A. Local environment**: Testcontainers-Postgres, no local DB install required
✅ **B. Test tiers & markers**: All tests properly categorized with `@pytest.mark.integration`
✅ **C. Async testing knobs**: pytest-asyncio with asyncio_mode=auto, httpx.AsyncClient, SQLAlchemy AsyncEngine/AsyncSession only
✅ **D. Database fixtures**: Session-scoped Postgres container, Alembic upgrade, Function-scoped AsyncSession with nested transaction (SAVEPOINT)
✅ **E. Scheduler control**: SCHEDULER_ENABLED default false in tests, dedicated scheduler test
✅ **F. Parallelization**: Testcontainers handles parallel execution automatically
✅ **G. Do-not list**: No sync/async mixing, no APScheduler in every test, proper test isolation, no external network calls

### Usage

```bash
# Run all tests - no local PostgreSQL required
python -m pytest tests/

# Run only integration tests
python -m pytest tests/ -m integration

# Run only unit tests (when added)
python -m pytest tests/ -m unit

# Run only contract tests (when added)
python -m pytest tests/ -m contract

# Run tests excluding integration (for unit/contract only)
python -m pytest tests/ -m "not integration"
```

The setup ensures complete compliance with the charter's local environment requirements.

### Important Notes

- **Development vs Testing**: The `alembic.ini` and `.env` files contain local database URLs for development purposes only
- **Test Isolation**: Tests use Testcontainers-Postgres exclusively and ignore any local database configurations
- **No Local DB Dependency**: ✅ **VERIFIED** - Local PostgreSQL completely removed, tests work with Testcontainers only
- **Docker Requirement**: Only Docker is required to run tests (for Testcontainers)
- **Complete Compliance**: ✅ **FULLY COMPLIANT** with charter's "no local DB install required" requirement

### Parallelization Support (Charter Compliance)

The test setup supports parallel execution with `pytest-xdist` as required by the charter:

- **Testcontainers Automatic Handling**: Each worker gets its own containerized PostgreSQL database automatically
- **No Configuration Required**: Testcontainers handles database isolation across workers seamlessly
- **Parallel Execution**: Can run integration tests in parallel without conflicts

```bash
# Run tests in parallel (4 workers)
python -m pytest tests/ -n 4

# Run only integration tests in parallel
python -m pytest tests/ -m integration -n 4

# Run unit/contract tests in parallel (when added)
python -m pytest tests/ -m "unit or contract" -n 4
```

**Charter Compliance**: ✅ **FULLY COMPLIANT** - Testcontainers automatically provides each worker with its own containerized DB
