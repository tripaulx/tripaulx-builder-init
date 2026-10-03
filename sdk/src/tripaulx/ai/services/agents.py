"""Operations on agents: team, attached skills, duplication and role change."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from django.db import transaction
from django.utils.translation import gettext as _

from tripaulx.ai.models import Agent, AgentRole, AgentSkill, Skill, TeamMember


def set_team(coordinator: Agent, specialists: Sequence[Agent]) -> None:
    """Rewrite the team as the ORDERED list given (position = index)."""
    with transaction.atomic():
        TeamMember.objects.filter(coordinator=coordinator).delete()
        TeamMember.objects.bulk_create(
            [
                TeamMember(coordinator=coordinator, specialist=agent, order=i)
                for i, agent in enumerate(specialists)
            ]
        )


def set_skills(agent: Agent, items: Sequence[tuple[Skill, bool]]) -> None:
    """Rewrite the attached skills as the ORDERED ``(skill, required)`` list."""
    with transaction.atomic():
        AgentSkill.objects.filter(agent=agent).delete()
        AgentSkill.objects.bulk_create(
            [
                AgentSkill(agent=agent, skill=skill, order=i, required=required)
                for i, (skill, required) in enumerate(items)
            ]
        )


def copy_name(name: str) -> str:
    """Return the name of a copy, unique among live agents."""
    base = _("%(name)s (copy)") % {"name": name}
    candidate, counter = base[:80], 2
    while Agent.objects.filter(name__iexact=candidate).exists():
        candidate = f"{base} {counter}"[:80]
        counter += 1
    return candidate


def duplicate(agent: Agent, *, by: Any) -> Agent:
    """Copy the agent (inactive) with the same team and skills."""
    with transaction.atomic():
        copy = Agent.objects.create(
            name=copy_name(agent.name),
            description=agent.description,
            role=agent.role,
            instructions=agent.instructions,
            input_template=agent.input_template,
            model_identifier=agent.model_identifier,
            effort=agent.effort,
            verbosity=agent.verbosity,
            temperature=agent.temperature,
            max_output_tokens=agent.max_output_tokens,
            output_schema=agent.output_schema,
            web_search=agent.web_search,
            web_search_domains=list(agent.web_search_domains or []),
            active=False,
            order=agent.order,
            created_by=by if getattr(by, "pk", None) else None,
        )
        set_team(copy, [m.specialist for m in agent.members.order_by("order", "id")])
        set_skills(
            copy,
            [(a.skill, a.required) for a in agent.agent_skills.order_by("order", "id")],
        )
        return copy


def role_change_complaint(agent: Agent, new_role: str) -> str | None:
    """Why changing the role would orphan a team, or ``None``."""
    if agent.role == new_role:
        return None
    if new_role == AgentRole.SPECIALIST and agent.members.exists():
        return _("Remove the team before making this agent a specialist.")
    if new_role == AgentRole.COORDINATOR:
        coordinators = (
            Agent.objects.filter(members__specialist=agent)
            .distinct()
            .values_list("name", flat=True)
        )
        if coordinators:
            return _(
                "This agent is in the team of: %(names)s. Remove it before "
                "making it a coordinator."
            ) % {"names": ", ".join(sorted(coordinators))}
    return None
