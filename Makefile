# NIM Sentinel Makefile
# Usage: make <target>

.PHONY: help install dev-install test lint format typecheck check-models up down logs clean

# Default target
help:
	@echo "NIM Sentinel - Available targets:"
	@echo "  install        - Install production dependencies"
	@echo "  dev-install    - Install all dependencies (dev + test + eval)"
	@echo "  test           - Run unit tests"
	@echo "  test-integration - Run integration tests (requires Docker)"
	@echo "  lint           - Run ruff linter"
	@echo "  format         - Format code with ruff and black"
	@echo "  typecheck      - Run mypy type checking"
	@echo "  check-models   - Verify NVIDIA models against API"
	@echo "  up             - Start local stack with docker-compose"
	@echo "  down           - Stop local stack"
	@echo "  logs           - View docker-compose logs"
	@echo "  clean          - Clean build artifacts"
	@echo "  pre-commit     - Run pre-commit hooks"
	@echo "  eval-smoke     - Run smoke evaluation suite"
	@echo "  eval-full      - Run full evaluation suite"

# Installation
install:
	pip install -e .

dev-install:
	pip install -e ".[dev,test,eval,ui,deploy]"
	pre-commit install

# Testing
test:
	pytest tests/ -v --tb=short -x

test-integration:
	pytest tests/ -v --tb=short -m integration

test-unit:
	pytest tests/ -v --tb=short -m unit

# Code quality
lint:
	ruff check src/ tests/ scripts/ --fix

format:
	ruff format src/ tests/ scripts/
	black src/ tests/ scripts/

typecheck:
	mypy src/

# Model verification
check-models:
	python scripts/check_models.py

# Docker
up:
	docker-compose -f deploy/docker/docker-compose.yml up -d

down:
	docker-compose -f deploy/docker/docker-compose.yml down

logs:
	docker-compose -f deploy/docker/docker-compose.yml logs -f

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Evaluation
eval-smoke:
	python evals/run_evals.py --smoke --push-langsmith

eval-full:
	python evals/run_evals.py --push-langsmith --fail-under

# Cleanup
clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Development workflow
dev-check: format lint typecheck test
	@echo "All checks passed!"

ci: lint typecheck test
	@echo "CI checks passed!"