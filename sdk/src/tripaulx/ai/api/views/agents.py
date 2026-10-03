"""``agents/``: CRUD (admins write), ``run`` (any member) and ``duplicate``."""

from __future__ import annotations

from django.db import connection
from django.db.models import QuerySet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from tripaulx.ai.models import Agent
from tripaulx.ai.services import agents as agent_service
from tripaulx.ai.services import origins
from tripaulx.ai.tasks import run as run_tasks

from ..permissions import IsAdminOrReadOnly
from ..serializers import AgentSerializer, RunRequestSerializer
from .common import METHODS_WITHOUT_PUT, UUID_URL
from .run_response import respond


class AgentViewSet(viewsets.ModelViewSet):
    """Whole list (tens, not thousands: no pagination), CRUD and actions."""

    serializer_class = AgentSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "id"
    lookup_value_regex = UUID_URL
    pagination_class = None
    http_method_names = METHODS_WITHOUT_PUT
    #: Declared so the ``run`` action can override it (a DRF quirk).
    throttle_scope = None

    def get_queryset(self) -> QuerySet:
        """Agents with links prefetched; ``?role=`` and ``?active=`` filters."""
        qs = (
            Agent.objects.select_related("created_by")
            .prefetch_related("members__specialist", "agent_skills__skill")
            .order_by("order", "name")
        )
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        active = self.request.query_params.get("active")
        if active in ("true", "false"):
            qs = qs.filter(active=(active == "true"))
        return qs

    def perform_destroy(self, instance: Agent) -> None:
        """Soft delete (``BaseModel``)."""
        instance.delete()

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        throttle_classes=[ScopedRateThrottle],
        throttle_scope="ai_run",
        serializer_class=RunRequestSerializer,
    )
    def run(self, request: Request, id: str | None = None) -> Response:
        """Run the agent on the input, as a ``django.tasks`` task.

        Immediate backend: 200 with the result whenever the body validated,
        even on a provider refusal (``ok:false``). Queue backend: 202 with a
        receipt to poll at ``executions/<task_id>/``.
        """
        agent = self.get_object()
        body = RunRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        result = run_tasks.enqueue_run(
            agent,
            body.validated_data["input"],
            schema=connection.schema_name,
            origin=origins.PLAYGROUND,
            user=request.user,
            context=body.validated_data.get("context") or "",
        )
        return respond(agent, result)

    @action(detail=True, methods=["post"])
    def duplicate(self, request: Request, id: str | None = None) -> Response:
        """Copy the agent (inactive) with the same team and skills."""
        copy = agent_service.duplicate(self.get_object(), by=request.user)
        return Response(
            AgentSerializer(copy, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )
