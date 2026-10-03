#!/usr/bin/env bash
# Fail when an SDK app has strings missing from (or untranslated in) pt_BR.
# Re-extracts messages with makemessages, then asks msgfmt for statistics.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export DJANGO_SETTINGS_MODULE=tests.project.settings
export PYTHONPATH="$ROOT/sdk/src:$ROOT/sdk"
status=0
for app_dir in "$ROOT"/sdk/src/tripaulx/*/locale/..; do
  app="$(cd "$app_dir" && pwd)"
  (cd "$app" && uv run django-admin makemessages -l pt_BR --no-obsolete >/dev/null)
  po="$app/locale/pt_BR/LC_MESSAGES/django.po"
  stats="$(msgfmt --check-format --check-domain --statistics -o /dev/null "$po" 2>&1)"
  echo "$(basename "$app"): $stats"
  if grep -qE "untranslated|fuzzy" <<<"$stats"; then status=1; fi
done
exit $status
