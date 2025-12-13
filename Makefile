.PHONY: help install test lint format clean docker-build docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -e .[dev]

test: ## Run tests
	pytest --cov=src --cov-report=term --cov-report=html

lint: ## Run linter
	ruff check .

format: ## Format code
	ruff format .

clean: ## Clean build artifacts
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build: ## Build Docker image
	docker-compose build

docker-up: ## Start services
	docker-compose up -d

docker-down: ## Stop services
	docker-compose down

docker-logs: ## View logs
	docker-compose logs -f

dev: docker-up ## Start development environment
	@echo "Development environment started!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
