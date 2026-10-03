#!/bin/sh
# =============================================================================
# Container HEALTHCHECK, per role (APP_ROLE).
#
#   web     GET /healthz/ on gunicorn. The SDK answers it before tenant
#           resolution, so any Host works; HEALTHCHECK_HOST only changes the
#           Host header sent. X-Forwarded-Proto: https mirrors what the
#           CapRover proxy sends, so SECURE_SSL_REDIRECT never turns the probe
#           into a 301 (curl -f would accept the redirect as healthy).
#   worker  there is no HTTP: healthy while PID 1 is db_worker (the
#           entrypoint uses `exec`, so the worker process IS PID 1).
# =============================================================================
case "${APP_ROLE:-web}" in
    worker)
        grep -q "db_worker" /proc/1/cmdline 2>/dev/null || exit 1
        ;;
    *)
        curl -fsS --max-time "${HEALTHCHECK_TIMEOUT:-4}" \
            -H "Host: ${HEALTHCHECK_HOST:-localhost}" \
            -H "X-Forwarded-Proto: https" \
            "http://127.0.0.1:8000${HEALTHCHECK_PATH:-/healthz/}" >/dev/null || exit 1
        ;;
esac
exit 0
