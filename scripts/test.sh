#!/usr/bin/env bash
set -euo pipefail

echo "==> Running Ruff Lint..."
ruff check .

echo "==> Running Ruff Format Check..."
ruff format --check .

echo "==> Running Mypy Static Type Checking..."
mypy app tests

echo "==> Running Pytest Test Suite..."
pytest "$@"
