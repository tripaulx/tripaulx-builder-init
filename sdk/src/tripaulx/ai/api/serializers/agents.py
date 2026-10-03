"""Agent serializers: full read and write with ordered team and skills.

``team`` and ``skills`` are ORDERED LISTS on write (ids; skills with
``required``) and on read (same shape, plus ``*_detail`` with names). The
list order IS the position. Coordinator/specialist rules are checked on the
RESULT of a PATCH (new value or the stored one).
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils.translation import gettext as _
from rest_framework import serializers

from tripaulx.ai import validators
from tripaulx.ai.models import Agent, AgentRole
from tripaulx.ai.services import agents as agent_service
from tripaulx.ai.services import prompt

from . import agent_links as links
from .common import checked_model, django_rule, require_text, unique_name, user_label


class AgentSummarySerializer(serializers.ModelSerializer):
    """The agent as a reference (in events, steps and lists)."""

    class Meta:
        model = Agent
        fields = ("id", "name", "slug", "role")
        read_only_fields = fields


class AgentSerializer(serializers.ModelSerializer):
    """Read and write of an agent."""

    role_label = serializers.CharField(source="get_role_display", read_only=True)
    temperature = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        coerce_to_string=False,
        required=False,
        allow_null=True,
    )
    team = serializers.ListField(
        child=serializers.UUIDField(), required=False, write_only=True
    )
    skills = links.SkillLinkSerializer(many=True, required=False, write_only=True)
    team_detail = serializers.SerializerMethodField()
    skills_detail = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "role",
            "role_label",
            "instructions",
            "input_template",
            "model_identifier",
            "effort",
            "verbosity",
            "temperature",
            "max_output_tokens",
            "output_schema",
            "web_search",
            "web_search_domains",
            "active",
            "order",
            "team",
            "team_detail",
            "skills",
            "skills_detail",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "created_at", "updated_at")

    def get_team_detail(self, obj: Agent) -> list[dict[str, Any]]:
        """Team members with names."""
        return links.team_detail(obj)

    def get_skills_detail(self, obj: Agent) -> list[dict[str, Any]]:
        """Attached skills with names and versions."""
        return links.skills_detail(obj)

    def get_created_by(self, obj: Agent) -> str:
        """Who created the agent."""
        return user_label(obj.created_by)

    def to_representation(self, instance: Agent) -> dict[str, Any]:
        """Add ``team`` and ``skills`` in the write shape."""
        data = super().to_representation(instance)
        data["team"] = [str(m.specialist_id) for m in links.live_members(instance)]
        data["skills"] = [
            {"id": str(link.skill_id), "required": link.required}
            for link in links.live_links(instance)
        ]
        return data

    def validate_name(self, value: str) -> str:
        """Require a name unique among live agents."""
        return unique_name(Agent, value, self.instance)

    def validate_instructions(self, value: str) -> str:
        """Instructions cannot be blank."""
        return require_text(value, _("Write the agent instructions."))

    def validate_input_template(self, value: str) -> str:
        """Require ``{input}`` and a formattable template."""
        complaint = prompt.template_complaint(value)
        if complaint:
            raise serializers.ValidationError(complaint)
        return value

    def validate_model_identifier(self, value: str) -> str:
        """Accept an active catalog model of the configured provider (or empty)."""
        return checked_model(value)

    def validate_temperature(self, value: Any) -> Any:
        """From 0 to 2."""
        return django_rule(validators.clean_temperature, value)

    def validate_output_schema(self, value: Any) -> dict:
        """Empty or an object JSON Schema."""
        return django_rule(validators.clean_output_schema, value)

    def validate_web_search_domains(self, value: Any) -> list[str]:
        """Clean hosts, at most 20."""
        return django_rule(validators.clean_search_domains, value)

    def validate_team(self, ids: list) -> list[Agent]:
        """Ordered active specialists."""
        return links.clean_team(ids, self.instance)

    def validate_skills(self, items: list[dict[str, Any]]) -> list:
        """Ordered active skills."""
        return links.clean_skills(items)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Role and team rules, on the RESULT of the PATCH."""
        attrs = super().validate(attrs)
        instance = self.instance
        role = attrs.get("role", getattr(instance, "role", AgentRole.SPECIALIST))
        # The role change comes first: "is in the team of X" is the most
        # specific complaint, and the team rule would be a symptom of it.
        if instance is not None and role != instance.role:
            complaint = agent_service.role_change_complaint(instance, role)
            if complaint:
                raise serializers.ValidationError({"role": complaint})
        if "team" in attrs:
            empty_team = not attrs["team"]
        else:
            empty_team = instance is None or not instance.members.exists()
        if role == AgentRole.COORDINATOR and empty_team:
            raise serializers.ValidationError(
                {"team": _("A coordinator needs at least one specialist.")}
            )
        if role == AgentRole.SPECIALIST and not empty_team:
            raise serializers.ValidationError(
                {"team": _("Only a coordinator has a team.")}
            )
        return attrs

    def create(self, validated_data: dict[str, Any]) -> Agent:
        """Create the agent with its team and skills."""
        team = validated_data.pop("team", [])
        skills = validated_data.pop("skills", [])
        user = getattr(self.context.get("request"), "user", None)
        if getattr(user, "pk", None):
            validated_data["created_by"] = user
        with transaction.atomic():
            agent = Agent.objects.create(**validated_data)
            agent_service.set_team(agent, team)
            agent_service.set_skills(agent, skills)
        return agent

    def update(self, instance: Agent, validated_data: dict[str, Any]) -> Agent:
        """Save the fields sent; rewrite team/skills only when sent."""
        team = validated_data.pop("team", None)
        skills = validated_data.pop("skills", None)
        with transaction.atomic():
            if validated_data:
                for name, value in validated_data.items():
                    setattr(instance, name, value)
                instance.save(update_fields=[*validated_data, "updated_at"])
            if team is not None:
                agent_service.set_team(instance, team)
            if skills is not None:
                agent_service.set_skills(instance, skills)
        return instance
