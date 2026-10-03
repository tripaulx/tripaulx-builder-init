"""Tenant resolution with health probes and static files short-circuited."""

from __future__ import annotations

from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django_tenants.middleware.main import TenantMainMiddleware

from ..views.health import healthz, readyz

PROBES = {
    "/healthz": healthz,
    "/healthz/": healthz,
    "/readyz": readyz,
    "/readyz/": readyz,
}


class TenantMiddleware(TenantMainMiddleware):
    """``TenantMainMiddleware`` that skips the Host lookup when it cannot apply.

    - Health probes are answered directly: the probe host is the container's
      internal address, which matches no ``Domain`` and would return 404.
    - Static files do not depend on a tenant, so they skip the database lookup
      and run on the public schema.
    """

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        """Answer probes, bypass static files, otherwise resolve the tenant."""
        probe = PROBES.get(request.path)
        if probe is not None:
            connection.set_schema_to_public()
            return probe(request)
        if settings.STATIC_URL and request.path.startswith(settings.STATIC_URL):
            connection.set_schema_to_public()
            return None
        return super().process_request(request)
