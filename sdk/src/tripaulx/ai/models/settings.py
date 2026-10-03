"""The workspace's AI settings: provider, model, call defaults and limits.

A singleton per tenant (fixed primary key ``1``): every workspace has its own
schema, so "one row per schema" already means "one per workspace". The model
is stored as ``provider`` + ``model_identifier`` and resolved in the shared
catalog; API keys live in :class:`~tripaulx.ai.models.AIKey`.

This model does not inherit ``BaseModel``: it is a singleton, and soft delete
makes no sense for it.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from tripaulx.ai.catalog import services as catalog
from tripaulx.ai.catalog.models import AIModel

from .choices import Effort
from .key import AIKey

SINGLETON_PK = 1


class AISettings(models.Model):
    """Settings of the workspace (singleton, primary key ``1``)."""

    enabled = models.BooleanField(
        _("enabled"), default=False, help_text=_("Turns AI on for this workspace.")
    )
    provider = models.CharField(_("provider"), max_length=32, default="openai")
    model_identifier = models.CharField(
        _("model"),
        max_length=120,
        blank=True,
        default="",
        help_text=_("Identifier of a catalog model of the chosen provider."),
    )
    effort = models.CharField(
        _("default reasoning effort"),
        max_length=16,
        choices=Effort.choices,
        default=Effort.INHERIT,
        blank=True,
    )
    max_output_tokens = models.PositiveIntegerField(
        _("default maximum output tokens"), null=True, blank=True
    )
    daily_cap_usd = models.DecimalField(
        _("daily cap (USD)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_(
            "Once reached, no new run starts until the next day. Empty means no cap."
        ),
    )
    store_content = models.BooleanField(
        _("store event content"),
        default=True,
        help_text=_(
            "Store the prompt, input and output of each call. Off keeps only "
            "metrics (tokens, cost, latency)."
        ),
    )
    retention_days = models.PositiveSmallIntegerField(
        _("content retention (days)"),
        default=90,
        help_text=_(
            "Event content older than this is purged; metrics stay. 0 keeps it forever."
        ),
    )
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("AI settings")
        verbose_name_plural = _("AI settings")

    def __str__(self) -> str:
        return str(_("AI settings"))

    @property
    def key(self) -> AIKey | None:
        """The active key of the chosen provider, or ``None``."""
        return AIKey.objects.active_for(self.provider)

    @property
    def api_key(self) -> str:
        """The decrypted key of the chosen provider (empty when missing)."""
        key = self.key
        return key.api_key if key is not None else ""

    @property
    def api_key_configured(self) -> bool:
        """Whether the chosen provider has an active and readable key."""
        key = self.key
        return key is not None and key.readable

    @property
    def model(self) -> AIModel | None:
        """The catalog row of the chosen model (active or not), or ``None``."""
        return catalog.find(self.provider, self.model_identifier)

    @property
    def ready(self) -> bool:
        """Whether everything needed to call the provider is set."""
        model = self.model
        return (
            self.enabled
            and self.api_key_configured
            and model is not None
            and model.active
        )

    def clean(self) -> None:
        """Refuse a model that is not in the catalog of the chosen provider."""
        super().clean()
        if self.model_identifier and self.model is None:
            raise ValidationError(
                {
                    "model_identifier": _(
                        "“%(model)s” is not a catalog model of %(provider)s."
                    )
                    % {"model": self.model_identifier, "provider": self.provider}
                }
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Force the singleton primary key."""
        self.pk = SINGLETON_PK
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> AISettings:
        """Return (creating it) the singleton of the current schema."""
        obj, _created = cls.objects.get_or_create(pk=SINGLETON_PK)
        return obj
