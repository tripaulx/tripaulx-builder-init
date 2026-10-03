#!/bin/sh
# =============================================================================
# Send the project to one CapRover app (normally called by ./deploy).
#
# Packs the code into a portable tar.gz (BSD and GNU tar) and uploads it with
# `caprover deploy --tarFile`. The server builds the image from
# captain-definition -> Dockerfile.
#
# Usage: scripts/caprover-deploy.sh <APP_NAME>
# Environment: CAPROVER_SERVER, CAPROVER_APP_TOKEN (an App Token, never the
# CapRover password).
# =============================================================================
set -e

APP_NAME="${1:-}"
CAPROVER_SERVER="${CAPROVER_SERVER:-}"
CAPROVER_APP_TOKEN="${CAPROVER_APP_TOKEN:-}"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARBALL="deploy.tar.gz"

log() { printf '[deploy %s] %s\n' "$(date -u +%FT%TZ)" "$1"; }
die() { printf '[deploy] ERROR: %s\n' "$1" >&2; exit 1; }

[ -n "$APP_NAME" ] || die "usage: scripts/caprover-deploy.sh <APP_NAME>"
[ -n "$CAPROVER_SERVER" ] || die "CAPROVER_SERVER is not set (.env.deploy)"
[ -n "$CAPROVER_APP_TOKEN" ] || die "CAPROVER_APP_TOKEN is not set (.env.deploy)"

# CapRover CLI: the global install, or npx (nothing gets installed).
run_caprover() {
    if command -v caprover >/dev/null 2>&1; then
        caprover "$@"
    elif command -v npx >/dev/null 2>&1; then
        npx --yes caprover "$@"
    else
        die "CapRover CLI not found. Install it (npm i -g caprover) or put npx on PATH."
    fi
}

# Portable tar: BSD tar matches `--exclude=NAME` against basenames at any
# depth, so anchored exclusions use `find -prune` plus `tar -T <list>`.
build_tar() {
    out="$1"
    list="$(mktemp)"
    find . \
        -path './.git' -prune -o \
        -path './.github' -prune -o \
        -path './.venv' -prune -o \
        -path './venv' -prune -o \
        -path './staticfiles' -prune -o \
        -path './media' -prune -o \
        -name node_modules -prune -o \
        -name __pycache__ -prune -o \
        -name .pytest_cache -prune -o \
        -name .ruff_cache -prune -o \
        -name .mypy_cache -prune -o \
        -type f \
            ! -name '*.pyc' \
            ! -name '*.log' \
            ! -name '.DS_Store' \
            ! -name '.env' \
            ! -name '.env.*' \
            ! -name '*.tar' \
            ! -name '*.tar.gz' \
            ! -name '*.tmp' \
        -print > "$list"
    count=$(wc -l < "$list" | tr -d ' ')
    [ "$count" -gt 0 ] || { rm -f "$list"; die "nothing to pack"; }
    log "packing $count files..."
    tar -czf "$out" -T "$list"
    rm -f "$list"
}

cd "$PROJECT_ROOT"

log "app:    $APP_NAME"
log "server: $CAPROVER_SERVER"
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    log "commit: $(git log -1 --oneline 2>/dev/null || echo n/a)"
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        log "WARNING: uncommitted changes will be included in the tar."
    fi
fi

rm -f "$TARBALL" "$TARBALL.tmp"
build_tar "$TARBALL.tmp"
mv "$TARBALL.tmp" "$TARBALL"
log "tar ready: $(du -h "$TARBALL" | cut -f1)"

log "uploading to CapRover (the image is built on the server)..."
if run_caprover deploy --appName "$APP_NAME" --caproverUrl "$CAPROVER_SERVER" \
    --appToken "$CAPROVER_APP_TOKEN" --tarFile "$TARBALL"; then
    rm -f "$TARBALL"
    log "deploy sent. Follow the build in the CapRover dashboard."
else
    die "deploy failed (the tar was kept in $TARBALL for inspection)"
fi
