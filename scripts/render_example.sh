#!/usr/bin/env bash
# Render template/ into example/ (gitignored) using the local SDK checkout.
#
# The template is copied without .git first, so uncommitted template changes
# are rendered too (Copier would otherwise render the last commit).
# Usage: scripts/render_example.sh [extra copier args]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$(mktemp -d)"
trap 'rm -rf "$SRC"' EXIT
cp "$ROOT/copier.yml" "$SRC/"
cp -R "$ROOT/template" "$SRC/template"
rm -rf "$ROOT/example"
uv run copier copy --trust --defaults \
  --data project_name="Example" \
  --data sdk_source=path \
  --data sdk_path="$ROOT/sdk" \
  "$@" "$SRC" "$ROOT/example"
