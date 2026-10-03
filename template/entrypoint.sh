#!/bin/sh
# =============================================================================
# Container entrypoint (CapRover). The same image runs two apps, by APP_ROLE:
#
#   web     (default) waits for the database, migrates, starts gunicorn
#   worker  waits for the database, starts `manage.py db_worker` (the
#           django.tasks queue). It does not migrate by default: the web app
#           migrates, and two containers migrating at once would race.
#
# Every variable comes from the CapRover app (App Configs > Env Vars).
# =============================================================================
set -e

log() { printf '[entrypoint %s] %s\n' "$(date -u +%FT%TZ)" "$1"; }

cd /app

DB_HOST="${DB_HOST:-}"
DB_PORT="${DB_PORT:-5432}"
APP_ROLE="${APP_ROLE:-web}"
case "$APP_ROLE" in
    web|worker) ;;
    *) log "ERROR: invalid APP_ROLE '$APP_ROLE' (use web or worker)"; exit 1 ;;
esac
log "container role: $APP_ROLE"

# 0. Required variables. Without this check a missing credential becomes a
#    crash loop with a psycopg traceback instead of a clear message.
missing=""
for var in SECRET_KEY APP_BASE_DOMAIN DB_NAME DB_USER DB_PASSWORD DB_HOST; do
    eval "val=\${$var:-}"
    [ -n "$val" ] || missing="$missing $var"
done
if [ -n "$missing" ]; then
    log "ERROR: required variables are missing or empty:$missing"
    log "Set them in the CapRover app (App Configs > Environment Variables)."
    exit 1
fi

# 1. Wait until PostgreSQL accepts TCP connections (up to 120s).
log "waiting for the database at ${DB_HOST}:${DB_PORT}..."
python - "$DB_HOST" "$DB_PORT" <<'PY'
import socket
import sys
import time

host, port = sys.argv[1], int(sys.argv[2])
for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=3):
            print("database reachable")
            break
    except OSError:
        time.sleep(2)
else:
    sys.exit("database unreachable after 120s")
PY

# 2. Multi-schema migrations (django-tenants), idempotent. RUN_MIGRATIONS=0
#    skips them; the worker defaults to 0 (RUN_MIGRATIONS=1 forces them).
if [ "$APP_ROLE" = "worker" ]; then
    RUN_MIGRATIONS="${RUN_MIGRATIONS:-0}"
fi
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    log "migrate_schemas --shared (public schema)"
    python manage.py migrate_schemas --shared --noinput
    log "bootstrap_workspace (public + initial workspace, idempotent)"
    python manage.py bootstrap_workspace
    log "migrate_schemas (every schema)"
    python manage.py migrate_schemas --noinput
else
    log "RUN_MIGRATIONS=0: skipping migrations"
fi

# 3. Worker: consume the task queue and nothing else (no HTTP).
#    db_worker requires the database backend; fail here with a clear message
#    instead of restarting silently. Stray spaces and trailing dots
#    ("database.") are tolerated, as in config/settings/base_parts/tasks.py.
if [ "$APP_ROLE" = "worker" ]; then
    backend="$(printf '%s' "${DJANGO_TASKS_BACKEND:-immediate}" | tr -d ' ' | sed 's/\.*$//')"
    case "$backend" in
        database|Database|DATABASE|*DatabaseBackend) ;;
        *)
            log "ERROR: the worker requires DJANGO_TASKS_BACKEND=database (got '${DJANGO_TASKS_BACKEND:-immediate}')"
            exit 1
            ;;
    esac
    log "starting db_worker (interval=${TASKS_WORKER_INTERVAL:-1}s queue=${TASKS_QUEUE_NAME:-default})"
    exec python manage.py db_worker \
        --interval "${TASKS_WORKER_INTERVAL:-1}" \
        --queue-name "${TASKS_QUEUE_NAME:-default}" \
        --no-startup-delay
fi

# 4. Web: gunicorn. Threads have a floor of 2: with 0 or 1 gunicorn falls back
#    to the "sync" worker (one request at a time), and a slow request would
#    queue /healthz/ behind it until Docker kills the container. A
#    non-numeric value also falls back to the floor.
threads="${GUNICORN_THREADS:-4}"
case "$threads" in
    ''|*[!0-9]*) threads=0 ;;
esac
if [ "$threads" -lt 2 ]; then
    log "WARNING: GUNICORN_THREADS='${GUNICORN_THREADS:-}' is below 2; using 2"
    threads=2
fi
workers="${GUNICORN_WORKERS:-2}"
timeout="${GUNICORN_TIMEOUT:-60}"
log "starting gunicorn on 0.0.0.0:8000 (workers=$workers threads=$threads timeout=$timeout)"
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$workers" \
    --threads "$threads" \
    --timeout "$timeout" \
    --control-socket /tmp/gunicorn.ctl \
    --access-logfile - \
    --error-logfile -
