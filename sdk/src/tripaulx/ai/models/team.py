"""Links of an agent: its team members and its attached skills."""

from __future__ import annotations

from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from .agent import Agent


class TeamMember(models.Model):
    """A specialist in a coordinator's team, with its position."""

    coordinator = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name="members"
    )
    specialist = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name="memberships"
    )
    order = models.PositiveSmallIntegerField(_("order"), default=0)

    class Meta:
        verbose_name = _("team member")
        verbose_name_plural = _("team members")
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["coordinator", "specialist"],
                name="tpsdk_ai_team_member_unique",
            ),
            models.CheckConstraint(
                condition=~Q(coordinator=F("specialist")),
                name="tpsdk_ai_team_member_not_self",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.coordinator_id} → {self.specialist_id} (#{self.order})"


class AgentSkill(models.Model):
    """A skill attached to an agent, with position and whether it is required."""

    agent = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name="agent_skills"
    )
    skill = models.ForeignKey(
        "tpsdk_ai.Skill", on_delete=models.CASCADE, related_name="skill_agents"
    )
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    required = models.BooleanField(
        _("required"),
        default=True,
        help_text=_(
            "A required skill without a published version makes the run fail; "
            "an optional one is skipped."
        ),
    )

    class Meta:
        verbose_name = _("agent skill")
        verbose_name_plural = _("agent skills")
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "skill"], name="tpsdk_ai_agent_skill_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.agent_id} · {self.skill_id} (#{self.order})"
