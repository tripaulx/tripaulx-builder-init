"""Skills: reusable instructions that enter the prompt of one or more agents.

A skill has two faces: the DRAFT (``instructions``, editable) and the
PUBLISHED VERSION (:class:`SkillVersion`, frozen). The runtime reads only the
published one: editing the draft changes nothing in production until someone
publishes, and every publication is recorded with number, note and author.

The parameters (model, effort, tokens) are read live, without versions: they
are operational, not content.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from tripaulx.core.models import BaseModel

from .choices import Effort
from .slug import unique_slug


class Skill(BaseModel):
    """Reusable instructions, with a draft and a published version."""

    name = models.CharField(_("name"), max_length=80)
    slug = models.SlugField(
        _("slug"), max_length=80, unique=True, blank=True, editable=False
    )
    description = models.CharField(
        _("description"), max_length=240, blank=True, default=""
    )
    instructions = models.TextField(
        _("instructions (draft)"),
        help_text=_("Markdown. Used at runtime only after it is published."),
    )
    model_identifier = models.CharField(
        _("model"),
        max_length=120,
        blank=True,
        default="",
        help_text=_("Overrides the agent's model while this skill is attached."),
    )
    effort = models.CharField(
        _("reasoning effort"),
        max_length=16,
        choices=Effort.choices,
        default=Effort.INHERIT,
        blank=True,
    )
    max_output_tokens = models.PositiveIntegerField(
        _("maximum output tokens"), null=True, blank=True
    )
    published_version = models.ForeignKey(
        "tpsdk_ai.SkillVersion",
        verbose_name=_("published version"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    active = models.BooleanField(_("active"), default=True)
    order = models.PositiveIntegerField(_("order"), default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("created by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = _("skill")
        verbose_name_plural = _("skills")
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                condition=Q(deleted_at__isnull=True),
                name="tpsdk_ai_skill_name_unique_alive",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Generate the slug on the first save."""
        if not self.slug:
            self.slug = unique_slug(self, self.name, default="skill")
        super().save(*args, **kwargs)

    @property
    def is_published(self) -> bool:
        """Whether a version is in force."""
        return self.published_version_id is not None

    @property
    def has_pending_draft(self) -> bool:
        """Whether the draft differs from the version in force (or none is)."""
        if self.published_version_id is None:
            return True
        return self.instructions.strip() != self.published_version.instructions.strip()


class SkillVersion(models.Model):
    """Immutable snapshot of a skill's instructions at publication time."""

    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField(_("number"))
    instructions = models.TextField(_("instructions"))
    note = models.CharField(_("note"), max_length=200, blank=True, default="")
    published_at = models.DateTimeField(_("published at"), auto_now_add=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("published by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    published_by_label = models.CharField(
        _("published by (name)"), max_length=254, blank=True, default=""
    )

    class Meta:
        verbose_name = _("skill version")
        verbose_name_plural = _("skill versions")
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(
                fields=["skill", "number"], name="tpsdk_ai_skill_version_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.skill_id} v{self.number}"
