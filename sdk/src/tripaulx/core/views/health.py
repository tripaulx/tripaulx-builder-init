"""Liveness and readiness probes.

Both are answered by :class:`tripaulx.core.middleware.TenantMiddleware` before
tenant resolution: CapRover/Swarm probes hit the container with an internal
host that never matches a workspace domain.
"""

from __future__ import annotations

import logging

from django.db import connection
from django.http import HttpRequest, JsonResponse

logger = logging.getLogger(__name__)


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness: the process is up. Never touches the database."""
    return JsonResponse({"status": "ok"})


def readyz(request: HttpRequest) -> JsonResponse:
    """Readiness: the process can reach the database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:  # noqa: BLE001 - any failure means "not ready"
        logger.exception("Readiness check failed")
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
