"""The model catalog: what each provider offers and what it costs.

One table in the public schema, shared by every workspace. Workspaces point at
a row by ``provider`` + ``identifier`` (never by foreign key: tenant tables
cannot reference rows of another schema reliably). ``identifier`` must match
exactly what the provider API expects in its ``model`` field.

Prices are USD per 1 million tokens. A missing price means "no price": events
keep ``cost_usd = None`` and the report counts them apart instead of making up
a number. ``TRIPAULX["AI_PRICE_OVERRIDES"]`` wins over these columns.

This model does not inherit ``BaseModel``: retiring a model is ``active =
False`` (workspaces that already chose it keep working), so soft delete adds
nothing, and an integer key keeps the admin readable.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class CostTier(models.IntegerChoices):
    """How expensive a model is compared to the others."""

    ECONOMY = 1, _("Economy")
    BALANCED = 2, _("Balanced")
    PREMIUM = 3, _("Premium")


def _price(verbose_name: str, help_text: str = "") -> models.DecimalField:
    """Build a nullable price column in USD per 1M tokens."""
    return models.DecimalField(
        verbose_name,
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text=help_text,
    )


class AIModel(models.Model):
    """A model a workspace can choose, with presentation and prices."""

    provider = models.CharField(_("provider"), max_length=32, db_index=True)
    identifier = models.CharField(
        _("identifier"),
        max_length=120,
        help_text=_("Exact model name in the provider API."),
    )
    label = models.CharField(_("label"), max_length=120)
    description = models.CharField(
        _("description"),
        max_length=240,
        blank=True,
        default="",
        help_text=_("One line on when to use this model."),
    )
    nickname = models.CharField(
        _("nickname"),
        max_length=40,
        blank=True,
        default="",
        help_text=_("One or two words about the model profile."),
    )
    cost_tier = models.PositiveSmallIntegerField(
        _("cost tier"), choices=CostTier.choices, null=True, blank=True
    )
    highlighted = models.BooleanField(
        _("highlighted"),
        default=False,
        help_text=_("Shown as a card when choosing the model."),
    )
    recommended = models.BooleanField(
        _("recommended"),
        default=False,
        help_text=_("Gets the “Recommended” badge."),
    )
    active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Uncheck to hide the model without deleting it."),
    )
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    supports_reasoning = models.BooleanField(
        _("supports reasoning"),
        default=False,
        help_text=_(
            "Reasoning models receive effort and never temperature. A wrong "
            "check makes the provider reject the call."
        ),
    )
    accepts_minimal_effort = models.BooleanField(
        _("accepts minimal effort"),
        default=True,
        help_text=_("Unchecked sends “low” instead of “minimal”."),
    )
    uses_thinking_budget = models.BooleanField(
        _("uses a thinking budget"),
        default=False,
        help_text=_(
            "The model takes a thinking token budget instead of an effort "
            "level (older Anthropic models)."
        ),
    )
    options = models.JSONField(
        _("provider options"),
        default=dict,
        blank=True,
        help_text=_("Provider-specific call options (see the AI docs)."),
    )
    input_price_usd_1m = _price(_("input price (USD/1M tokens)"))
    cached_price_usd_1m = _price(
        _("cached input price (USD/1M tokens)"), _("Empty uses the input price.")
    )
    output_price_usd_1m = _price(_("output price (USD/1M tokens)"))
    prices_updated_on = models.DateField(_("prices updated on"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("AI model")
        verbose_name_plural = _("AI models")
        ordering = ["provider", "order", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "identifier"], name="tpsdk_ai_model_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider} · {self.label}"

    @property
    def key(self) -> str:
        """The ``provider:identifier`` pair used by price overrides."""
        return f"{self.provider}:{self.identifier}"

    @property
    def has_price(self) -> bool:
        """Whether at least the input or the output price is set."""
        return (
            self.input_price_usd_1m is not None or self.output_price_usd_1m is not None
        )
