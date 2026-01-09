# Makefile for YouTube Summarizer (using uv)

.PHONY: help install install-dev test format lint type-check clean run example check

# Default target
help:
	@echo "Available commands:"
	@echo "  install      Install the package (uv sync)"
	@echo "  install-dev  Install with development dependencies"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage"
	@echo "  format       Format code with black"
	@echo "  lint         Lint code with ruff"
	@echo "  type-check   Type check with mypy"
	@echo "  clean        Clean up cache and build artifacts"
	@echo "  run          Run the CLI directly"
	@echo "  example      Run with an example video"
	@echo "  check        Run all quality checks"

# Installation
install:
	uv sync

install-dev:
	uv sync --dev

# Running example
example:
	@echo "Running with example video..."
	uv run yt-summarizer --provider openrouter https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Testing
test:
	uv run pytest

test-cov:
	uv run pytest --cov=yt_summarizer --cov-report=html --cov-report=term

# Code quality
format:
	uv run black yt_summarizer tests
	uv run ruff check --fix yt_summarizer tests

lint:
	uv run ruff check yt_summarizer tests

type-check:
	uv run mypy yt_summarizer

# Cleaning
clean:
	@echo "Cleaning up caches and artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ 2>/dev/null || true
	rm -rf dist/ build/ 2>/dev/null || true

# Running
run:
	uv run yt-summarizer

# Development helpers
check: format lint type-check test
	@echo "All checks passed!"

# Build distribution
build:
	uv build

# Lock file management
lock:
	uv lock

# Update dependencies
update:
	uv sync --upgrade