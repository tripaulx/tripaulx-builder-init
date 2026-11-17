"""Workspace lookup: whether a slug exists or can be taken (public schema)."""

from __future__ import annotations

from django.db import connection
from django.http import Http404
from django_tenants.utils import get_public_schema_name
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from tripaulx.tenants.services.domains import workspace_origin
from tripaulx.tenants.services.lookup import slug_status

from ..schema import untyped
from .base import AccountsAPIView


class WorkspaceLookupView(AccountsAPIView):
    """Answer the login ("which workspace?") and signup (is it free?) screens.

    Always 200: ``exists`` and ``available`` tell the cases apart, ``reason``
    explains an unusable slug.
    """

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_lookup"

    def initial(self, request: Request, *args: object, **kwargs: object) -> None:
        """Only on the public schema."""
        if connection.schema_name != get_public_schema_name():
            raise Http404
        super().initial(request, *args, **kwargs)

    @untyped
    def get(self, request: Request, slug: str) -> Response:
        """Describe ``slug``."""
        found = slug_status(slug.strip().lower())
        origin = workspace_origin(request, found.slug) if found.exists else ""
        return Response(
            {
                "slug": found.slug,
                "exists": found.exists,
                "available": found.available,
                "name": found.name,
                "reason": found.reason,
                "workspace_url": origin,
                "api_url": f"{origin}/api" if origin else "",
            }
        )
