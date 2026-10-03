"""Agents: who talks to the AI on behalf of the workspace.

An agent is identity plus rules (``instructions``), a template of the user
message, model parameters (all optional, inherited from the settings) and
skills attached in order. There are two roles:

- SPECIALIST: receives the input and answers.
- COORDINATOR: has an ordered TEAM of specialists. The runtime runs each one
  in sequence (each sees what the previous ones produced) and then the
  coordinator consolidates.

"A team member is always a specialist, and a specialist has no team" keeps
the graph a tree of height 1, so no cycle is possible. The database only
checks self-reference; the serializer checks the rest.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from tripaulx.core.models import BaseModel

from .choices import AgentRole, Effort, Verbosity
from .slug import unique_slug


class Agent(BaseModel):
    """AI profile: identity, prompt, parameters, team and skills."""

    name = models.CharField(_("name"), max_length=80)
    slug = models.SlugField(
        _("slug"), max_length=80, unique=True, blank=True, editable=False
    )
    description = models.CharField(
        _("description"), max_length=240, blank=True, default=""
    )
    role = models.CharField(
        _("role"),
        max_length=16,
        choices=AgentRole.choices,
        default=AgentRole.SPECIALIST,
        db_index=True,
    )
    instructions = models.TextField(
        _("instructions"),
        help_text=_("Identity and rules of the agent (a system prompt layer)."),
    )
    input_template = models.TextField(
        _("input template"),
        default="{input}",
        help_text=_("User message. Placeholders: {input} and {context}."),
    )
    model_identifier = models.CharField(
        _("model"),
        max_length=120,
        blank=True,
        default="",
        help_text=_("Empty inherits the model of the workspace settings."),
    )
    effort = models.CharField(
        _("reasoning effort"),
        max_length=16,
        choices=Effort.choices,
        default=Effort.INHERIT,
        blank=True,
    )
    verbosity = models.CharField(
        _("verbosity"),
        max_length=8,
        choices=Verbosity.choices,
        default=Verbosity.INHERIT,
        blank=True,
    )
    temperature = models.DecimalField(
        _("temperature"),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Sent only to models without reasoning."),
    )
    max_output_tokens = models.PositiveIntegerField(
        _("maximum output tokens"), null=True, blank=True
    )
    output_schema = models.JSONField(
        _("output schema"),
        default=dict,
        blank=True,
        help_text=_("Empty is free text. An object JSON Schema requires JSON."),
    )
    web_search = models.BooleanField(
        _("web search"),
        default=False,
        help_text=_("The agent may search the web before answering."),
    )
    web_search_domains = models.JSONField(
        _("web search domains"),
        default=list,
        blank=True,
        help_text=_("Only these sites (and subdomains). Empty means any site."),
    )
    active = models.BooleanField(_("active"), default=True)
    order = models.PositiveIntegerField(_("order"), default=0)
    team = models.ManyToManyField(
        "self",
        through="TeamMember",
        through_fields=("coordinator", "specialist"),
        symmetrical=False,
        related_name="coordinators",
        blank=True,
    )
    skills = models.ManyToManyField(
        "tpsdk_ai.Skill", through="AgentSkill", related_name="agents", blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("created by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = _("agent")
        verbose_name_plural = _("agents")
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                condition=Q(deleted_at__isnull=True),
                name="tpsdk_ai_agent_name_unique_alive",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Generate the slug on the first save."""
        if not self.slug:
            self.slug = unique_slug(self, self.name, default="agent")
        super().save(*args, **kwargs)

    @property
    def is_coordinator(self) -> bool:
        """Whether the agent coordinates a team."""
        return self.role == AgentRole.COORDINATOR

    def live_members(self) -> models.QuerySet:
        """Team members that still exist and are active, in order."""
        return (
            self.members.filter(
                specialist__deleted_at__isnull=True, specialist__active=True
            )
            .select_related("specialist")
            .order_by("order", "id")
        )

    def live_skills(self) -> models.QuerySet:
        """Attached skills that still exist and are active, in order."""
        return (
            self.agent_skills.filter(skill__deleted_at__isnull=True, skill__active=True)
            .select_related("skill", "skill__published_version")
            .order_by("order", "id")
        )
