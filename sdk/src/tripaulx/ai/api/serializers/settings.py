"""Serializers of the AI settings, the catalog and the "test AI" result.

The API KEY never leaves through here, not even encrypted: it has its own
write-only route (``key/``) and what comes back is the audit trail.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _
from rest_framework import serializers

from tripaulx.ai import providers
from tripaulx.ai.catalog.models import AIModel
from tripaulx.ai.models import AISettings
from tripaulx.ai.services import prices
from tripaulx.ai.services.model_choice import InvalidModelChoice, check_provider

from .common import checked_model


class AISettingsSerializer(serializers.ModelSerializer):
    """The settings in force; the provider/model pair is checked as a whole."""

    provider_label = serializers.SerializerMethodField()
    model_label = serializers.SerializerMethodField()
    api_key_configured = serializers.BooleanField(read_only=True)
    ready = serializers.BooleanField(read_only=True)
    daily_cap_usd = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=False,
        required=False,
        allow_null=True,
        min_value=0,
    )

    class Meta:
        model = AISettings
        fields = (
            "enabled",
            "provider",
            "provider_label",
            "model_identifier",
            "model_label",
            "api_key_configured",
            "ready",
            "effort",
            "max_output_tokens",
            "daily_cap_usd",
            "store_content",
            "retention_days",
            "updated_at",
        )
        read_only_fields = ("updated_at",)

    def get_provider_label(self, obj: AISettings) -> str:
        """Display label of the provider."""
        return providers.label_of(obj.provider)

    def get_model_label(self, obj: AISettings) -> str:
        """Display label of the chosen model."""
        model = obj.model
        return model.label if model else ""

    def validate_provider(self, value: str) -> str:
        """Accept only a registered provider."""
        try:
            return check_provider(value)
        except InvalidModelChoice as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Check the model against the provider of the PATCH RESULT.

        A PATCH may send only one of the two; without merging them, changing
        only the provider would leave the old model orphaned, failing only at
        call time. An inactive model may not be chosen now, but a model that
        was deactivated after being chosen is kept when it is not resent.
        """
        attrs = super().validate(attrs)
        provider = attrs.get("provider", getattr(self.instance, "provider", "openai"))
        identifier = attrs.get(
            "model_identifier", getattr(self.instance, "model_identifier", "")
        )
        provider_changed = provider != getattr(self.instance, "provider", None)
        if "model_identifier" in attrs or provider_changed:
            try:
                checked = checked_model(identifier, provider)
            except serializers.ValidationError as exc:
                if "model_identifier" in attrs or not identifier:
                    raise serializers.ValidationError(
                        {"model_identifier": exc.detail}
                    ) from exc
                raise serializers.ValidationError(
                    {"model_identifier": _("Choose a model of the new provider.")}
                ) from exc
            attrs["model_identifier"] = checked
        return attrs


class AIModelSerializer(serializers.ModelSerializer):
    """A catalog model as the model picker shows it (prices with overrides)."""

    cost_tier_label = serializers.CharField(
        source="get_cost_tier_display", read_only=True, default=""
    )
    prices = serializers.SerializerMethodField()

    class Meta:
        model = AIModel
        fields = (
            "identifier",
            "label",
            "description",
            "nickname",
            "cost_tier",
            "cost_tier_label",
            "highlighted",
            "recommended",
            "supports_reasoning",
            "prices",
        )
        read_only_fields = fields

    def get_prices(self, obj: AIModel) -> dict[str, float | None] | None:
        """USD per 1M tokens (input, cached, output), or ``None``."""
        found = prices.prices_for(obj)
        if found is None:
            return None
        return {
            name: float(value) if value is not None else None
            for name, value in (
                ("input", found.input),
                ("cached", found.cached),
                ("output", found.output),
            )
        }


class ProviderCatalogSerializer(serializers.Serializer):
    """A provider and its ACTIVE models (no table: providers are a registry)."""

    value = serializers.CharField()
    label = serializers.CharField()
    models = AIModelSerializer(many=True)


class ProbeResultSerializer(serializers.Serializer):
    """The "test AI" result; ``ok=False`` is the diagnosis, not an API error."""

    ok = serializers.BooleanField(read_only=True)
    latency_ms = serializers.IntegerField(read_only=True)
    model = serializers.CharField(read_only=True)
    answer = serializers.CharField(read_only=True)
    error = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)
