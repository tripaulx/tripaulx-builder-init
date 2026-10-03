#!/usr/bin/env bash
# =============================================================================
# check - the local quality gate (also run by ./deploy before shipping).
#
#   bash scripts/check.sh
#
# Stops at the first failure: ruff lint, ruff format, then pytest (needs the
# local PostgreSQL, see ./pg).
# =============================================================================
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR"

log() { printf '[check] %s\n' "$*"; }

log "ruff check"
uv run ruff check --no-fix .

log "ruff format --check"
uv run ruff format --check .

log "pytest"
uv run pytest -q

log "all green."
