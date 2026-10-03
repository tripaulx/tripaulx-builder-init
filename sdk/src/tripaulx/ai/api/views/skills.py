"""``skills/``: CRUD (admins write), ``publish``, ``versions`` and ``duplicate``."""

from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from tripaulx.ai.models import Skill
from tripaulx.ai.services import skills as skill_service

from ..permissions import IsAdminOrReadOnly
from ..serializers import (
    PublishSkillSerializer,
    SkillSerializer,
    SkillVersionSerializer,
)
from .common import METHODS_WITHOUT_PUT, UUID_URL


class SkillViewSet(viewsets.ModelViewSet):
    """Skills with draft and published versions."""

    serializer_class = SkillSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "id"
    lookup_value_regex = UUID_URL
    pagination_class = None
    http_method_names = METHODS_WITHOUT_PUT

    def get_queryset(self) -> QuerySet:
        """Skills in order; ``?active=`` filter."""
        qs = Skill.objects.select_related("published_version", "created_by").order_by(
            "order", "name"
        )
        active = self.request.query_params.get("active")
        if active in ("true", "false"):
            qs = qs.filter(active=(active == "true"))
        return qs

    def perform_destroy(self, instance: Skill) -> None:
        """Soft delete (``BaseModel``)."""
        instance.delete()

    @action(detail=True, methods=["post"], serializer_class=PublishSkillSerializer)
    def publish(self, request: Request, id: str | None = None) -> Response:
        """Freeze the draft as the next version (the one runs use)."""
        skill = self.get_object()
        body = PublishSkillSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            skill_service.publish(
                skill, by=request.user, note=body.validated_data["note"]
            )
        except skill_service.NothingToPublish as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        skill.refresh_from_db()
        return Response(
            SkillSerializer(skill, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["get"], serializer_class=SkillVersionSerializer)
    def versions(self, request: Request, id: str | None = None) -> Response:
        """List published versions, newest first (up to 50)."""
        skill = self.get_object()
        return Response(
            SkillVersionSerializer(skill.versions.all()[:50], many=True).data
        )

    @action(detail=True, methods=["post"])
    def duplicate(self, request: Request, id: str | None = None) -> Response:
        """Copy draft and parameters into a new, unpublished skill."""
        copy = skill_service.duplicate(self.get_object(), by=request.user)
        return Response(
            SkillSerializer(copy, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )
