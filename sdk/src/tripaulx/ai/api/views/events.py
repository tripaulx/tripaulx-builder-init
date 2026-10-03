"""``events/``: paginated list, detail, ``report`` and ``recent`` (read-only).

Every member sees metadata (tokens, cost, status, latency). The content
(system prompt, input, output, raw response, error detail) is returned only
to workspace owners and admins: it may hold anything users typed.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.request import Request
from rest_framework.response import Response

from tripaulx.ai.models import AIEvent, EventStatus
from tripaulx.ai.services import origins
from tripaulx.ai.services import report as report_service

from ..pagination import EventPagination
from ..permissions import is_admin
from ..serializers import AIEventContentSerializer, AIEventSerializer
from .common import UUID_URL


def _days(value: str | None, *, default: int = 30) -> int:
    message = _("Enter a number of days between 1 and 365.")
    try:
        days = int(value) if value not in (None, "") else default
    except ValueError as exc:
        raise ValidationError({"days": [message]}) from exc
    if not 1 <= days <= 365:
        raise ValidationError({"days": [message]})
    return days


def _choice(name: str, value: str, allowed: set[str]) -> str:
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValidationError(
            {name: [_("Use one of: %(choices)s.") % {"choices": choices}]}
        )
    return value


class AIEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only: events are recorded, never edited."""

    serializer_class = AIEventSerializer
    pagination_class = EventPagination
    lookup_field = "id"
    lookup_value_regex = UUID_URL
    filter_backends = [SearchFilter]
    search_fields = ["agent_label", "reference", "error_message", "model_identifier"]

    def get_serializer_class(self) -> Any:
        """Content only on the detail, and only for admins."""
        if self.action == "retrieve" and is_admin(self.request):
            return AIEventContentSerializer
        return AIEventSerializer

    def get_queryset(self) -> QuerySet:
        """Filter by days (list), origin, status, agent, model, run, error, skill."""
        qs = AIEvent.objects.select_related("agent").order_by("-created_at", "-id")
        p = self.request.query_params
        if self.action == "list":
            start = timezone.localdate() - timedelta(days=_days(p.get("days")) - 1)
            qs = qs.filter(created_at__date__gte=start)
        if p.get("origin"):
            qs = qs.filter(
                origin=_choice("origin", p["origin"], set(origins.origins()))
            )
        if p.get("status"):
            allowed = {value for value, _label in EventStatus.choices}
            qs = qs.filter(status=_choice("status", p["status"], allowed))
        for param, lookup in (
            ("agent", "agent_id"),
            ("model", "model_identifier"),
            ("execution_id", "execution_id"),
            ("error_code", "error_code"),
            ("provider", "provider"),
        ):
            if p.get(param):
                qs = qs.filter(**{lookup: p[param]})
        if p.get("skill"):
            qs = qs.filter(skills__contains=[{"id": p["skill"]}])
        return qs

    @action(detail=False, methods=["get"])
    def report(self, request: Request) -> Response:
        """Totals, breakdowns and daily series of ``?days=`` (7, 30 or 90)."""
        days = _days(request.query_params.get("days"))
        if days not in report_service.ALLOWED_DAYS:
            allowed = ", ".join(str(d) for d in report_service.ALLOWED_DAYS)
            return Response(
                {"days": [_("Use one of: %(choices)s.") % {"choices": allowed}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(report_service.report(days))

    @action(detail=False, methods=["get"])
    def recent(self, request: Request) -> Response:
        """List the latest ``?limit=`` events (1 to 50), without pagination."""
        try:
            limit = int(request.query_params.get("limit") or 15)
        except ValueError:
            limit = 15
        events = report_service.recent(limit)
        return Response(AIEventSerializer(events, many=True).data)
