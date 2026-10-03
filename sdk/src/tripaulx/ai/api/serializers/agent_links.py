"""Team and skill links of an agent: validation and read-out."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _
from rest_framework import serializers

from tripaulx.ai.models import Agent, AgentRole, Skill


class SkillLinkSerializer(serializers.Serializer):
    """One attached skill in the write payload."""

    id = serializers.UUIDField()
    required = serializers.BooleanField(required=False, default=True)


def clean_team(ids: list, instance: Agent | None) -> list[Agent]:
    """Ordered, unique, active specialists (never the agent itself)."""
    if len(set(ids)) != len(ids):
        raise serializers.ValidationError(_("A specialist is repeated in the team."))
    if instance is not None and instance.pk in ids:
        raise serializers.ValidationError(_("The agent cannot be in its own team."))
    found = {a.pk: a for a in Agent.objects.filter(pk__in=ids)}
    members = []
    for pk in ids:
        agent = found.get(pk)
        if agent is None:
            raise serializers.ValidationError(
                _("Agent not found (id %(id)s).") % {"id": pk}
            )
        if agent.role != AgentRole.SPECIALIST:
            raise serializers.ValidationError(
                _("“%(name)s” is not a specialist.") % {"name": agent.name}
            )
        if not agent.active:
            raise serializers.ValidationError(
                _("“%(name)s” is inactive.") % {"name": agent.name}
            )
        members.append(agent)
    return members


def clean_skills(items: list[dict[str, Any]]) -> list[tuple[Skill, bool]]:
    """Ordered, unique, active skills with their ``required`` flag."""
    ids = [item["id"] for item in items]
    if len(set(ids)) != len(ids):
        raise serializers.ValidationError(_("A skill is repeated."))
    found = {s.pk: s for s in Skill.objects.filter(pk__in=ids)}
    links = []
    for item in items:
        skill = found.get(item["id"])
        if skill is None:
            raise serializers.ValidationError(
                _("Skill not found (id %(id)s).") % {"id": item["id"]}
            )
        if not skill.active:
            raise serializers.ValidationError(
                _("The skill “%(name)s” is inactive.") % {"name": skill.name}
            )
        links.append((skill, bool(item.get("required", True))))
    return links


def live_members(agent: Agent) -> Any:
    """Team links whose specialist was not deleted, in order."""
    return (
        agent.members.filter(specialist__deleted_at__isnull=True)
        .select_related("specialist")
        .order_by("order", "id")
    )


def live_links(agent: Agent) -> Any:
    """Skill links whose skill was not deleted, in order."""
    return (
        agent.agent_skills.filter(skill__deleted_at__isnull=True)
        .select_related("skill", "skill__published_version")
        .order_by("order", "id")
    )


def team_detail(agent: Agent) -> list[dict[str, Any]]:
    """Return the team with names, for display."""
    return [
        {
            "id": str(m.specialist_id),
            "name": m.specialist.name,
            "slug": m.specialist.slug,
            "order": i,
            "active": m.specialist.active,
        }
        for i, m in enumerate(live_members(agent))
    ]


def skills_detail(agent: Agent) -> list[dict[str, Any]]:
    """Return the attached skills with names and versions, for display."""
    return [
        {
            "id": str(link.skill_id),
            "name": link.skill.name,
            "slug": link.skill.slug,
            "order": i,
            "required": link.required,
            "active": link.skill.active,
            "is_published": link.skill.is_published,
            "published_version": link.skill.published_version.number
            if link.skill.published_version_id
            else None,
        }
        for i, link in enumerate(live_links(agent))
    ]
