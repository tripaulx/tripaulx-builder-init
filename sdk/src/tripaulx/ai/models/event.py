"""Usage event: one row per provider call, on success AND on error.

It is the table behind the cost report and the success rate, so it is "fat":
what was asked (model, parameters, prompt), what came back (text, tokens,
latency) and what it cost. Immutable: no soft delete, no ``updated_at``.

- ``cost_usd = None`` means "no price", never zero; the report counts those
  apart instead of adding a made-up cost.
- ``agent_label``/``user_label``/``model_identifier`` are frozen at the time,
  so the report survives deleting the agent, the user or the model.
- The content (``system_prompt``, ``input_text``, ``output_text``,
  ``raw_response``) is optional and purgeable; the metrics stay.

``execution_id`` groups the calls of one run (a team makes N+1 events) and
``origin``/``reference`` say where it came from (a value of the origin
registry plus a free reference such as ``invoice:<uuid>``).
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .agent import Agent
from .choices import EventStatus, ExecutionStep


def _tokens(verbose_name: str) -> models.PositiveIntegerField:
    """Build a nullable token counter."""
    return models.PositiveIntegerField(verbose_name, null=True, blank=True)


class AIEvent(models.Model):
    """One call to an AI provider, with metrics, cost and optional content."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    execution_id = models.UUIDField(_("execution"), db_index=True)
    step = models.CharField(
        _("step"),
        max_length=16,
        choices=ExecutionStep.choices,
        default=ExecutionStep.SINGLE,
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    origin = models.CharField(_("origin"), max_length=32, db_index=True)
    reference = models.CharField(
        _("reference"), max_length=120, blank=True, default="", db_index=True
    )
    operation = models.CharField(_("operation"), max_length=24, default="run")
    agent = models.ForeignKey(
        Agent,
        verbose_name=_("agent"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    agent_label = models.CharField(
        _("agent (name)"), max_length=80, blank=True, default=""
    )
    skills = models.JSONField(_("skills"), default=list, blank=True)
    provider = models.CharField(_("provider"), max_length=32, blank=True, default="")
    model_identifier = models.CharField(
        _("requested model"), max_length=120, blank=True, default="", db_index=True
    )
    responded_model = models.CharField(
        _("responding model"), max_length=120, blank=True, default=""
    )
    status = models.CharField(
        _("status"), max_length=16, choices=EventStatus.choices, db_index=True
    )
    http_status = models.PositiveSmallIntegerField(_("HTTP"), null=True, blank=True)
    error_code = models.CharField(
        _("error code"), max_length=40, blank=True, default="", db_index=True
    )
    error_message = models.TextField(_("error message"), blank=True, default="")
    error_detail = models.TextField(_("technical detail"), blank=True, default="")
    latency_ms = models.PositiveIntegerField(_("latency (ms)"), null=True, blank=True)
    input_tokens = _tokens(_("input tokens"))
    output_tokens = _tokens(_("output tokens"))
    total_tokens = _tokens(_("total tokens"))
    cached_tokens = _tokens(_("cached tokens"))
    reasoning_tokens = _tokens(_("reasoning tokens"))
    web_searches = models.PositiveSmallIntegerField(_("web searches"), default=0)
    cost_usd = models.DecimalField(
        _("cost (USD)"), max_digits=12, decimal_places=6, null=True, blank=True
    )
    input_price_usd_1m = models.DecimalField(
        _("input price (USD/1M tokens)"),
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
    )
    output_price_usd_1m = models.DecimalField(
        _("output price (USD/1M tokens)"),
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
    )
    system_prompt = models.TextField(_("system prompt"), blank=True, default="")
    input_text = models.TextField(_("input"), blank=True, default="")
    output_text = models.TextField(_("output"), blank=True, default="")
    raw_response = models.JSONField(_("raw response"), null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    user_label = models.CharField(_("user (name)"), max_length=254, blank=True)
    content_purged_at = models.DateTimeField(
        _("content purged at"), null=True, blank=True
    )

    class Meta:
        verbose_name = _("AI event")
        verbose_name_plural = _("AI events")
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["origin", "-created_at"], name="tpsdk_ai_ev_origin"),
            models.Index(fields=["agent", "-created_at"], name="tpsdk_ai_ev_agent"),
            models.Index(fields=["status", "-created_at"], name="tpsdk_ai_ev_status"),
        ]

    def __str__(self) -> str:
        agent = self.agent_label or "—"
        return f"{self.get_status_display()} · {agent} · {self.model_identifier}"

    @property
    def succeeded(self) -> bool:
        """Whether the call succeeded."""
        return self.status == EventStatus.SUCCESS
