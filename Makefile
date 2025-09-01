# Protectogram v3.1 - Development Makefile
.PHONY: help dev test test-unit test-integration test-critical clean install lint format security deploy-staging deploy-prod

# Default Python and environment
PYTHON := python3.11
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python

# Environment variables
export ENVIRONMENT := development
export PYTHONPATH := $(PWD)

# Help target
help: ## Show this help message
	@echo "Protectogram v3.1 - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development setup
install: ## Install dependencies and setup development environment
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -r requirements-test.txt
	@echo "✅ Dependencies installed"

install-dev: install ## Install development dependencies
	$(PIP) install -e .
	@echo "✅ Development environment ready"

# Database management
db-setup: ## Setup local PostgreSQL database
	@echo "Setting up local database..."
	@docker run -d --name protectogram-postgres \
		-e POSTGRES_PASSWORD=localpass \
		-e POSTGRES_DB=protectogram_dev \
		-p 5432:5432 \
		postgis/postgis:15-3.3
	@sleep 5
	@echo "✅ PostgreSQL with PostGIS ready"

db-migrate: ## Run database migrations
	$(PYTHON_VENV) -m alembic upgrade head
	@echo "✅ Database migrations applied"

db-migration: ## Create new database migration
	@read -p "Migration message: " message; \
	$(PYTHON_VENV) -m alembic revision --autogenerate -m "$$message"
	@echo "✅ Migration created"

# Redis setup
redis-setup: ## Start Redis container
	@echo "Starting Redis..."
	@docker run -d --name protectogram-redis -p 6379:6379 redis:7-alpine
	@echo "✅ Redis ready"

# Development server
dev: ## Start development environment (FastAPI + Celery)
	@echo "Starting Protectogram development environment..."
	@$(MAKE) db-setup || true
	@$(MAKE) redis-setup || true
	@sleep 2
	@$(MAKE) db-migrate
	@echo "Starting FastAPI server..."
	@$(PYTHON_VENV) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
	@echo "Starting Celery worker..."
	@$(PYTHON_VENV) -m celery -A app.celery_app worker --loglevel=info &
	@echo "Starting Celery beat..."
	@$(PYTHON_VENV) -m celery -A app.celery_app beat --loglevel=info &
	@echo "✅ Development environment running"
	@echo "FastAPI: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

dev-stop: ## Stop development environment
	@echo "Stopping development services..."
	@pkill -f "uvicorn app.main:app" || true
	@pkill -f "celery.*app.celery_app" || true
	@docker stop protectogram-postgres protectogram-redis || true
	@echo "✅ Development environment stopped"

# Testing
test: ## Run all tests with coverage
	@echo "Running all tests..."
	@export ENVIRONMENT=test && \
	$(PYTHON_VENV) -m pytest tests/ \
		-v --tb=short \
		--asyncio-mode=auto \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--maxfail=1
	@echo "✅ All tests completed"

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	@export ENVIRONMENT=test && \
	$(PYTHON_VENV) -m pytest tests/ -m "unit" -v --asyncio-mode=auto
	@echo "✅ Unit tests completed"

test-integration: ## Run integration tests
	@echo "Running integration tests..."
	@export ENVIRONMENT=test && \
	$(PYTHON_VENV) -m pytest tests/ -m "integration" -v --asyncio-mode=auto
	@echo "✅ Integration tests completed"

test-critical: ## Run critical safety tests
	@echo "Running CRITICAL safety tests..."
	@export ENVIRONMENT=test && \
	$(PYTHON_VENV) -m pytest tests/ -m "critical" -v -s --tb=short --asyncio-mode=auto
	@echo "✅ Critical safety tests completed"

test-panic: ## Run panic-specific tests
	@echo "Running panic system tests..."
	@export ENVIRONMENT=test && \
	$(PYTHON_VENV) -m pytest tests/ -m "panic" -v --asyncio-mode=auto
	@echo "✅ Panic tests completed"

test-trip: ## Run trip-specific tests
	@echo "Running trip system tests..."
	@export ENVIRONMENT=test && \
	$(PYTHON_VENV) -m pytest tests/ -m "trip" -v --asyncio-mode=auto
	@echo "✅ Trip tests completed"

test-suspension: ## Run suspension logic tests
	@echo "Running suspension logic tests..."
	@export ENVIRONMENT=test && \
	$(PYTHON_VENV) -m pytest tests/ -m "suspension" -v -s --asyncio-mode=auto
	@echo "✅ Suspension tests completed"

test-speed: ## Test panic button response time
	@echo "Testing panic button response time..."
	@$(PYTHON_VENV) scripts/test_panic_speed.py --target-time 2.0
	@echo "✅ Speed test completed"

# Code quality
lint: ## Run linting (ruff, mypy)
	@echo "Running linting..."
	@$(PYTHON_VENV) -m ruff check app tests
	@$(PYTHON_VENV) -m mypy app
	@echo "✅ Linting completed"

format: ## Format code with ruff
	@echo "Formatting code..."
	@$(PYTHON_VENV) -m ruff format app tests scripts
	@$(PYTHON_VENV) -m ruff check --fix app tests scripts
	@echo "✅ Code formatted"

security: ## Run security audit
	@echo "Running security audit..."
	@$(PYTHON_VENV) -m bandit -r app/ -f json -o security-report.json
	@$(PYTHON_VENV) -m safety check
	@echo "✅ Security audit completed"

# Pre-commit checks
pre-commit: format lint test-critical ## Run pre-commit checks
	@echo "✅ Pre-commit checks passed"

# Deployment
deploy-staging: test ## Deploy to staging environment
	@echo "Deploying to staging..."
	@fly deploy --config fly.staging.toml --build-arg ENVIRONMENT=staging
	@echo "✅ Deployed to staging"

deploy-prod: test ## Deploy to production environment
	@echo "Deploying to production..."
	@fly deploy --config fly.toml --build-arg ENVIRONMENT=production
	@echo "✅ Deployed to production"

# Health checks
health: ## Check application health
	@echo "Checking application health..."
	@curl -f http://localhost:8000/health || (echo "❌ Health check failed" && exit 1)
	@echo "✅ Application healthy"

# Monitoring
logs-staging: ## View staging logs
	@fly logs --app protectogram-staging

logs-prod: ## View production logs
	@fly logs --app protectogram

monitor: ## Start monitoring (Flower for Celery)
	@$(PYTHON_VENV) -m celery -A app.celery_app flower --port=5555 &
	@echo "✅ Monitoring started at http://localhost:5555"

# Cleanup
clean: ## Clean up development environment
	@echo "Cleaning up..."
	@$(MAKE) dev-stop
	@docker rm -f protectogram-postgres protectogram-redis || true
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@rm -rf .pytest_cache htmlcov .coverage
	@echo "✅ Cleanup completed"

clean-all: clean ## Clean everything including venv
	@echo "Deep cleaning..."
	@rm -rf $(VENV)
	@rm -rf .mypy_cache
	@echo "✅ Deep cleanup completed"

# Documentation
docs: ## Generate API documentation
	@echo "Generating documentation..."
	@$(PYTHON_VENV) -c "import app.main; print('API docs available at http://localhost:8000/docs')"

# Default target
.DEFAULT_GOAL := help
