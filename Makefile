.PHONY: help install setup test test-unit test-integration test-contract lint type-check format clean db-migrate db-upgrade db-downgrade db-reset deploy-staging deploy-prod health-check logs metrics

# Default target
help:
	@echo "Protectogram - Development Commands"
	@echo "=================================="
	@echo "Development:"
	@echo "  install        Install dependencies with uv"
	@echo "  setup          Setup development environment"
	@echo "  test           Run all tests"
	@echo "  test-unit      Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-contract  Run contract tests only"
	@echo "  lint           Run ruff linting"
	@echo "  type-check     Run mypy type checking"
	@echo "  format         Format code with ruff"
	@echo "  clean          Clean build artifacts"
	@echo ""
	@echo "Database:"
	@echo "  db-migrate     Create new migration"
	@echo "  db-upgrade     Apply migrations"
	@echo "  db-downgrade   Rollback migration"
	@echo "  db-reset       Reset database (staging only)"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy-staging Deploy to staging"
	@echo "  deploy-prod    Deploy to production"
	@echo ""
	@echo "Monitoring:"
	@echo "  health-check   Check application health"
	@echo "  logs           View application logs"
	@echo "  metrics        View application metrics"

# Development
install:
	@echo "Installing dependencies..."
	uv pip install -r requirements.txt
	uv pip install -e ".[dev]"

setup: install
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example"; fi
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "Setup complete!"

test:
	@echo "Running all tests..."
	pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -v

test-contract:
	@echo "Running contract tests..."
	pytest tests/contract/ -v

lint:
	@echo "Running ruff linting..."
	ruff check app/ tests/

type-check:
	@echo "Running mypy type checking..."
	mypy app/ tests/

format:
	@echo "Formatting code with ruff..."
	ruff format app/ tests/

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Database
db-migrate:
	@echo "Creating new migration..."
	@read -p "Enter migration message: " message; \
	alembic revision --autogenerate -m "$$message"

db-upgrade:
	@echo "Applying migrations..."
	alembic upgrade head

db-downgrade:
	@echo "Rolling back migration..."
	alembic downgrade -1

db-reset:
	@echo "Resetting database (staging only)..."
	@read -p "Are you sure? This will drop all data! (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		alembic downgrade base; \
		alembic upgrade head; \
		echo "Database reset complete!"; \
	else \
		echo "Database reset cancelled."; \
	fi

# Deployment
deploy-staging:
	@echo "Deploying to staging..."
	@if [ ! -f fly.toml ]; then echo "Error: fly.toml not found"; exit 1; fi
	fly deploy --config fly.toml
	@echo "Staging deployment complete!"

deploy-prod:
	@echo "Deploying to production..."
	@read -p "Are you sure you want to deploy to production? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		fly deploy --config fly.toml --app protectogram-prod; \
		echo "Production deployment complete!"; \
	else \
		echo "Production deployment cancelled."; \
	fi

# Monitoring
health-check:
	@echo "Checking application health..."
	@if [ -z "$$APP_URL" ]; then \
		echo "Error: APP_URL environment variable not set"; \
		echo "Example: APP_URL=https://protectogram-staging.fly.dev make health-check"; \
		exit 1; \
	fi
	curl -f "$$APP_URL/health/live" && echo " - Live check passed"
	curl -f "$$APP_URL/health/ready" && echo " - Ready check passed"
	curl -f "$$APP_URL/metrics" && echo " - Metrics endpoint accessible"

logs:
	@echo "Viewing application logs..."
	fly logs --app protectogram-staging

metrics:
	@echo "Viewing application metrics..."
	@if [ -z "$$APP_URL" ]; then \
		echo "Error: APP_URL environment variable not set"; \
		echo "Example: APP_URL=https://protectogram-staging.fly.dev make metrics"; \
		exit 1; \
	fi
	curl -s "$$APP_URL/metrics" | grep -E "(panic_|call_|scheduler_)" || echo "No metrics found"

# CI/CD helpers
ci-install:
	@echo "Installing dependencies for CI..."
	pip install -r requirements.txt

ci-test:
	@echo "Running CI tests..."
	pytest tests/ --cov=app --cov-report=xml --cov-report=term-missing

ci-lint:
	@echo "Running CI linting..."
	ruff check app/ tests/
	ruff format --check app/ tests/

ci-type-check:
	@echo "Running CI type checking..."
	mypy app/ tests/

ci-security:
	@echo "Running security checks..."
	bandit -r app/ -f json
	safety check
