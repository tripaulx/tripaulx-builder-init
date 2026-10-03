"""``settings/``, ``providers/``, ``test/`` and ``dashboard/``.

The settings are a SINGLETON per tenant, so ``settings/<id>/`` would suggest a
second one: hence an ``APIView``, not a ViewSet. Members read; only owners
and admins change the settings or run the "test AI" call (it spends the
workspace's tokens).
"""

from __future__ import annotations

from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from tripaulx.accounts.api.permissions import IsWorkspaceAdmin
from tripaulx.ai import providers
from tripaulx.ai.catalog import services as catalog
from tripaulx.ai.models import AISettings
from tripaulx.ai.services import dashboard, probe

from ..permissions import IsAdminOrReadOnly
from ..serializers import (
    AIEventSerializer,
    AISettingsSerializer,
    ProbeResultSerializer,
    ProviderCatalogSerializer,
)


class AISettingsView(APIView):
    """Read (members) and partial update (owners and admins)."""

    permission_classes = [IsAdminOrReadOnly]
    serializer_class = AISettingsSerializer

    def get(self, request: Request) -> Response:
        """Return the settings of the workspace (created on first read)."""
        return Response(AISettingsSerializer(AISettings.load()).data)

    def patch(self, request: Request) -> Response:
        """Save only what came in the body (PATCH, never PUT)."""
        serializer = AISettingsSerializer(
            AISettings.load(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProvidersView(APIView):
    """Every registered provider with its active catalog models.

    A provider with an empty list is information: the UI can say "no model
    in the catalog yet" instead of hiding the option.
    """

    serializer_class = ProviderCatalogSerializer

    def get(self, request: Request) -> Response:
        """Return the catalog grouped by provider (one query)."""
        grouped = catalog.active_by_provider()
        data = [
            {"value": value, "label": label, "models": grouped.get(value, [])}
            for value, label in providers.choices()
        ]
        return Response(ProviderCatalogSerializer(data, many=True).data)


class ProbeView(APIView):
    """The "test AI" call with the stored key and model.

    200 EVEN WHEN THE CALL FAILS: the user clicked to find out what is wrong,
    so "the provider rejected the key" is the right answer, not an error of
    this route (a 401 would even log the user out in some clients). 400 is
    kept for an incomplete configuration. AI need not be enabled: testing
    before turning it on is the natural order.
    """

    permission_classes = [IsWorkspaceAdmin]
    serializer_class = ProbeResultSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_test"

    def post(self, request: Request) -> Response:
        """Run the test call."""
        settings = AISettings.load()
        if not settings.api_key_configured:
            detail = _(
                "No API key for %(provider)s. Add the key in the AI settings."
            ) % {"provider": providers.label_of(settings.provider)}
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
        if settings.model is None:
            return Response(
                {"detail": _("Choose a model and save before testing.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = probe.probe(settings, user=request.user)
        return Response(ProbeResultSerializer(result).data)


class DashboardView(APIView):
    """Every number of the AI hub in one call."""

    @extend_schema(
        operation_id="ai_dashboard",
        responses=OpenApiTypes.OBJECT,
        description="Settings state, budget, counts, usage and recent events.",
    )
    def get(self, request: Request) -> Response:
        """Return settings state, budget, counts and usage."""
        data = dashboard.dashboard()
        last = data.pop("last_event")
        recent = data.pop("recent")
        data["last_event"] = AIEventSerializer(last).data if last else None
        data["recent"] = AIEventSerializer(recent, many=True).data
        return Response(data)
