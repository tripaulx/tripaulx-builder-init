"""Skill serializers: the editable draft, the published version and history."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _
from rest_framework import serializers

from tripaulx.ai.models import Skill, SkillVersion

from .common import checked_model, require_text, unique_name, user_label


class SkillSerializer(serializers.ModelSerializer):
    """The skill as edited. ``instructions`` is the DRAFT; runs read the version."""

    is_published = serializers.BooleanField(read_only=True)
    published_version = serializers.SerializerMethodField()
    published_at = serializers.SerializerMethodField()
    has_pending_draft = serializers.BooleanField(read_only=True)
    agents = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Skill
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "instructions",
            "model_identifier",
            "effort",
            "max_output_tokens",
            "active",
            "order",
            "is_published",
            "published_version",
            "published_at",
            "has_pending_draft",
            "agents",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "created_at", "updated_at")

    def get_published_version(self, obj: Skill) -> int | None:
        """Return the number of the version in force."""
        return obj.published_version.number if obj.published_version_id else None

    def get_published_at(self, obj: Skill) -> Any:
        """When the version in force was published."""
        return obj.published_version.published_at if obj.published_version_id else None

    def get_agents(self, obj: Skill) -> list[dict[str, str]]:
        """Live agents using the skill."""
        links = obj.skill_agents.filter(agent__deleted_at__isnull=True).select_related(
            "agent"
        )
        return [
            {"id": str(link.agent_id), "name": link.agent.name, "slug": link.agent.slug}
            for link in links.order_by("agent__name")
        ]

    def get_created_by(self, obj: Skill) -> str:
        """Who created the skill."""
        return user_label(obj.created_by)

    def validate_name(self, value: str) -> str:
        """Require a name unique among live skills."""
        return unique_name(Skill, value, self.instance)

    def validate_instructions(self, value: str) -> str:
        """Refuse a blank draft."""
        return require_text(value, _("Write the skill instructions."))

    def validate_model_identifier(self, value: str) -> str:
        """Accept an active catalog model of the configured provider (or empty)."""
        return checked_model(value)

    def create(self, validated_data: dict[str, Any]) -> Skill:
        """Record the author."""
        user = getattr(self.context.get("request"), "user", None)
        if getattr(user, "pk", None):
            validated_data["created_by"] = user
        return super().create(validated_data)


class SkillVersionSerializer(serializers.ModelSerializer):
    """A published (immutable) version."""

    published_by = serializers.CharField(source="published_by_label", read_only=True)

    class Meta:
        model = SkillVersion
        fields = (
            "id",
            "number",
            "instructions",
            "note",
            "published_at",
            "published_by",
        )
        read_only_fields = fields


class PublishSkillSerializer(serializers.Serializer):
    """The body of ``publish/``: an optional note."""

    note = serializers.CharField(
        required=False, allow_blank=True, max_length=200, default=""
    )
