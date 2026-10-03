"""Event serializers: metadata for every member, content for admins only."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from tripaulx.ai.models import AIEvent
from tripaulx.ai.providers.common import parse_json_object
from tripaulx.ai.services import origins

from .agents import AgentSummarySerializer


class AIEventSerializer(serializers.ModelSerializer):
    """Metrics and identification, WITHOUT the content (prompt/input/output)."""

    agent = AgentSummarySerializer(read_only=True)
    origin_label = serializers.SerializerMethodField()
    model = serializers.CharField(source="model_identifier", read_only=True)
    cost_usd = serializers.DecimalField(
        max_digits=12, decimal_places=6, coerce_to_string=False, read_only=True
    )
    user = serializers.CharField(source="user_label", read_only=True)

    class Meta:
        model = AIEvent
        fields = (
            "id",
            "created_at",
            "execution_id",
            "step",
            "position",
            "origin",
            "origin_label",
            "reference",
            "agent",
            "agent_label",
            "skills",
            "provider",
            "model",
            "responded_model",
            "status",
            "http_status",
            "error_code",
            "error_message",
            "latency_ms",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cached_tokens",
            "reasoning_tokens",
            "web_searches",
            "cost_usd",
            "user",
            "content_purged_at",
        )
        read_only_fields = fields

    def get_origin_label(self, obj: AIEvent) -> str:
        """Label of the origin in the registry."""
        return origins.label(obj.origin)


class AIEventContentSerializer(AIEventSerializer):
    """Metadata plus content and price snapshots (workspace admins only)."""

    data = serializers.SerializerMethodField()
    input_price_usd_1m = serializers.DecimalField(
        max_digits=10, decimal_places=4, coerce_to_string=False, read_only=True
    )
    output_price_usd_1m = serializers.DecimalField(
        max_digits=10, decimal_places=4, coerce_to_string=False, read_only=True
    )

    class Meta(AIEventSerializer.Meta):
        fields = AIEventSerializer.Meta.fields + (
            "system_prompt",
            "input_text",
            "output_text",
            "data",
            "raw_response",
            "error_detail",
            "input_price_usd_1m",
            "output_price_usd_1m",
        )
        read_only_fields = fields

    def get_data(self, obj: AIEvent) -> dict[str, Any] | None:
        """Return the output as JSON when the agent asked for a schema."""
        if not obj.output_text or not obj.agent_id or not obj.agent.output_schema:
            return None
        return parse_json_object(obj.output_text)
