.PHONY: help install install-dev setup test lint format clean docker-up docker-down migrate db-upgrade db-downgrade run-api run-frontend

# Variables
PYTHON := python3
PIP := pip3
DOCKER_COMPOSE := docker-compose
PYTEST := pytest
BLACK := black
RUFF := ruff
MYPY := mypy

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)NovaAvatar Development Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	pre-commit install
	@echo "$(GREEN)✓ Development environment ready$(NC)"

setup: install-dev ## Complete development setup
	@echo "$(BLUE)Setting up NovaAvatar development environment...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(YELLOW)Created .env file from .env.example$(NC)"; \
		echo "$(YELLOW)Please edit .env with your API keys$(NC)"; \
	fi
	mkdir -p storage/generated storage/videos storage/queue logs
	@echo "$(GREEN)✓ Setup complete!$(NC)"

# Testing
test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(PYTEST) tests/ -v

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(PYTEST) tests/unit/ -v -m unit

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(PYTEST) tests/integration/ -v -m integration

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(PYTEST) tests/ -v --cov=services --cov=api --cov=frontend --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/index.html$(NC)"

test-watch: ## Run tests in watch mode
	$(PYTEST) tests/ -v --looponfail

# Code Quality
lint: ## Run all linters
	@echo "$(BLUE)Running linters...$(NC)"
	$(RUFF) check services/ api/ frontend/ config/
	$(BLACK) --check services/ api/ frontend/ config/
	$(MYPY) services/ api/ frontend/ config/
	@echo "$(GREEN)✓ All checks passed$(NC)"

format: ## Auto-format code
	@echo "$(BLUE)Formatting code...$(NC)"
	$(BLACK) services/ api/ frontend/ config/ tests/
	$(RUFF) check --fix services/ api/ frontend/ config/
	isort services/ api/ frontend/ config/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

format-check: ## Check code formatting
	@echo "$(BLUE)Checking code format...$(NC)"
	$(BLACK) --check services/ api/ frontend/ config/
	isort --check-only services/ api/ frontend/ config/

type-check: ## Run type checking
	@echo "$(BLUE)Running type checks...$(NC)"
	$(MYPY) services/ api/ frontend/ config/

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files

# Docker
docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) build

docker-up: ## Start all services with Docker Compose
	@echo "$(BLUE)Starting Docker services...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "API: http://localhost:8000"
	@echo "Frontend: http://localhost:7860"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000"

docker-up-dev: ## Start development services
	@echo "$(BLUE)Starting development services...$(NC)"
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up -d

docker-down: ## Stop all Docker services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	$(DOCKER_COMPOSE) down

docker-logs: ## View Docker logs
	$(DOCKER_COMPOSE) logs -f

docker-logs-api: ## View API logs
	$(DOCKER_COMPOSE) logs -f api

docker-logs-frontend: ## View frontend logs
	$(DOCKER_COMPOSE) logs -f frontend

docker-shell-api: ## Open shell in API container
	$(DOCKER_COMPOSE) exec api /bin/bash

docker-shell-frontend: ## Open shell in frontend container
	$(DOCKER_COMPOSE) exec frontend /bin/bash

docker-test: ## Run tests in Docker
	@echo "$(BLUE)Running tests in Docker...$(NC)"
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.test.yml run --rm test

docker-clean: ## Remove all Docker containers, volumes, and images
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	$(DOCKER_COMPOSE) down -v --rmi all

# Database
db-upgrade: ## Upgrade database to latest migration
	@echo "$(BLUE)Upgrading database...$(NC)"
	alembic upgrade head

db-downgrade: ## Downgrade database by one migration
	@echo "$(BLUE)Downgrading database...$(NC)"
	alembic downgrade -1

db-revision: ## Create new migration (use MESSAGE="description")
	@echo "$(BLUE)Creating migration: $(MESSAGE)$(NC)"
	alembic revision --autogenerate -m "$(MESSAGE)"

db-history: ## Show migration history
	alembic history

db-current: ## Show current migration
	alembic current

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		alembic downgrade base; \
		alembic upgrade head; \
		echo "$(GREEN)✓ Database reset$(NC)"; \
	fi

db-shell: ## Open PostgreSQL shell
	$(DOCKER_COMPOSE) exec postgres psql -U novaavatar -d novaavatar

# Running the application
run-api: ## Run API server locally
	@echo "$(BLUE)Starting API server...$(NC)"
	uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

run-frontend: ## Run Gradio frontend locally
	@echo "$(BLUE)Starting Gradio frontend...$(NC)"
	$(PYTHON) run.py

run-dev: ## Run both API and frontend (requires tmux)
	@echo "$(BLUE)Starting API and frontend...$(NC)"
	tmux new-session -d -s novaavatar 'make run-api'
	tmux split-window -h 'make run-frontend'
	tmux attach -t novaavatar

# Cleaning
clean: ## Clean up generated files
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage coverage.xml
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-storage: ## Clean storage directory (generated files)
	@echo "$(YELLOW)Cleaning storage directory...$(NC)"
	rm -rf storage/generated/* storage/videos/* storage/queue/*
	@echo "$(GREEN)✓ Storage cleaned$(NC)"

clean-all: clean clean-storage docker-clean ## Deep clean (includes Docker)

# Monitoring
monitor-logs: ## Monitor application logs
	tail -f logs/*.log

monitor-metrics: ## Open Prometheus metrics
	@echo "Opening Prometheus at http://localhost:9090"
	@open http://localhost:9090 2>/dev/null || xdg-open http://localhost:9090 2>/dev/null || echo "Open http://localhost:9090 in your browser"

monitor-dashboard: ## Open Grafana dashboard
	@echo "Opening Grafana at http://localhost:3000"
	@open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || echo "Open http://localhost:3000 in your browser"

# CI/CD
ci-test: format-check lint test ## Run all CI checks locally

ci-build: ## Build for CI
	$(DOCKER_COMPOSE) build --no-cache

# Documentation
docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation...$(NC)"
	@echo "README: http://localhost:8080/README.md"
	@$(PYTHON) -m http.server 8080

# Load Testing
load-test: ## Run load tests with Locust
	@echo "$(BLUE)Starting Locust load testing...$(NC)"
	locust -f tests/load/locustfile.py --host=http://localhost:8000

load-test-headless: ## Run load tests headless (10 users, 2/sec spawn rate, 60s)
	@echo "$(BLUE)Running headless load test...$(NC)"
	locust -f tests/load/locustfile.py --host=http://localhost:8000 --users 10 --spawn-rate 2 --run-time 60s --headless

# Security
security-check: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	bandit -r services/ api/ frontend/ config/
	safety check

# Benchmarking
benchmark: ## Run performance benchmarks
	@echo "$(BLUE)Running benchmarks...$(NC)"
	$(PYTEST) tests/benchmark/ -v --benchmark-only

# Version management
version: ## Show current version
	@echo "NovaAvatar v$(shell grep -m 1 version pyproject.toml | cut -d'"' -f2)"

# Quick shortcuts
up: docker-up ## Alias for docker-up
down: docker-down ## Alias for docker-down
logs: docker-logs ## Alias for docker-logs
shell: docker-shell-api ## Alias for docker-shell-api

# Default target
.DEFAULT_GOAL := help
