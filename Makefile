.PHONY: help install test test-unit test-integration lint format migrate-up migrate-down clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -e .
	pip install -e ".[dev]"

test: ## Run all tests
	pytest -q tests/ --import-mode=importlib

test-unit: ## Run unit tests only
	pytest -q tests/unit --import-mode=importlib

test-integration: ## Run integration tests only
	pytest -q tests/integration --import-mode=importlib

lint: ## Run linting
	ruff check .

format: ## Format code
	ruff format .

migrate-up: ## Run database migrations up
	alembic upgrade head

migrate-down: ## Rollback last migration
	alembic downgrade -1

migrate-revision: ## Create new migration (usage: make migrate-revision name=migration_name)
	alembic revision --autogenerate -m "$(name)"

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
