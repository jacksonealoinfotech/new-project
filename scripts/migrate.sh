#!/usr/bin/env bash
set -euo pipefail

echo "==> Running Alembic Database Migrations..."
alembic upgrade head
echo "==> Migrations completed successfully."
