"""Input and output of ``agents/<id>/run/``.

The answer is 200 whenever the body validated, including a provider refusal
(``ok=false`` plus ``error``): a 4xx would make session interceptors treat an
expired provider key as an expired login. Money goes out as a NUMBER.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from tripaulx.ai.conf import app_settings

from .agents import AgentSummarySerializer


class RunRequestSerializer(serializers.Serializer):
    """The body: the input and, optionally, a context (text or JSON as text)."""

    input = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        error_messages={"blank": _("Enter the input text.")},
    )
    context = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_input(self, value: str) -> str:
        """At most ``AI_MAX_INPUT_CHARS`` characters."""
        return _limited(value, app_settings.AI_MAX_INPUT_CHARS)

    def validate_context(self, value: str) -> str:
        """At most ``AI_MAX_CONTEXT_CHARS`` characters."""
        return _limited(value, app_settings.AI_MAX_CONTEXT_CHARS)


def _limited(value: str, size: int) -> str:
    """Refuse ``value`` longer than ``size`` characters."""
    if len(value or "") > int(size):
        raise serializers.ValidationError(
            _("Ensure this field has no more than %(size)s characters.")
            % {"size": size}
        )
    return value


class StepSerializer(serializers.Serializer):
    """One call of the run (reads ``StepResult``)."""

    position = serializers.IntegerField()
    step = serializers.CharField()
    agent = AgentSummarySerializer()
    ok = serializers.BooleanField()
    text = serializers.CharField(allow_blank=True)
    data = serializers.JSONField(allow_null=True)
    model = serializers.CharField(source="model_identifier", allow_blank=True)
    latency_ms = serializers.IntegerField()
    total_tokens = serializers.IntegerField()
    cost_usd = serializers.DecimalField(
        max_digits=12, decimal_places=6, coerce_to_string=False, allow_null=True
    )
    event_id = serializers.UUIDField(allow_null=True)
    error_code = serializers.SerializerMethodField()
    error_message = serializers.SerializerMethodField()

    def get_error_code(self, obj: Any) -> str:
        """Error code of the step (empty on success)."""
        return obj.error.code if obj.error else ""

    def get_error_message(self, obj: Any) -> str:
        """Error sentence of the step (empty on success)."""
        return obj.error.message if obj.error else ""


class RunResultSerializer(serializers.Serializer):
    """The whole ``RunResult``: final output, totals, steps and the error."""

    ok = serializers.BooleanField()
    execution_id = serializers.UUIDField()
    agent = AgentSummarySerializer()
    text = serializers.CharField(allow_blank=True)
    data = serializers.JSONField(allow_null=True)
    model = serializers.CharField(source="model_identifier", allow_blank=True)
    latency_ms = serializers.IntegerField()
    tokens = serializers.SerializerMethodField()
    cost_usd = serializers.DecimalField(
        max_digits=12, decimal_places=6, coerce_to_string=False, allow_null=True
    )
    cost_unknown = serializers.BooleanField()
    steps = StepSerializer(many=True)
    error = serializers.SerializerMethodField()
    #: Sources cited by web search: ``[{"url", "title"}]``.
    sources = serializers.SerializerMethodField()

    def get_tokens(self, obj: Any) -> dict[str, int]:
        """Input, output and total tokens of the run."""
        return {
            "input": obj.input_tokens,
            "output": obj.output_tokens,
            "total": obj.total_tokens,
        }

    def get_error(self, obj: Any) -> dict[str, Any] | None:
        """Return the run error, or ``None``."""
        return obj.error.as_dict() if obj.error else None

    def get_sources(self, obj: Any) -> list[dict[str, str]]:
        """Web sources of the final step."""
        return [dict(s) for s in obj.sources or ()]
