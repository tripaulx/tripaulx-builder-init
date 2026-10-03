"""Serializers of the provider keys: the audit trail out, the key in only.

The key value travels in ONE direction (in, write-only). What comes back is
who added or closed each key and when; ``api_key_encrypted`` is never in
``fields``. A masked value (``sk-...abcd``) stays out too: the last digits of
a secret are secret.
"""

from __future__ import annotations

from rest_framework import serializers

from tripaulx.ai.models import AIKey
from tripaulx.ai.services import keys as key_service


class AIKeySerializer(serializers.ModelSerializer):
    """One key WITHOUT its value: who added it, who closed it, and when."""

    created_by = serializers.CharField(source="created_by_label", read_only=True)
    closed_by = serializers.CharField(source="closed_by_label", read_only=True)
    closed_reason_label = serializers.CharField(
        source="get_closed_reason_display", read_only=True
    )
    readable = serializers.BooleanField(read_only=True)

    class Meta:
        model = AIKey
        fields = (
            "id",
            "provider",
            "created_at",
            "created_by",
            "closed_at",
            "closed_by",
            "closed_reason",
            "closed_reason_label",
            "readable",
        )
        read_only_fields = fields


class ProviderKeyStateSerializer(serializers.Serializer):
    """The key state of one provider: the active key (or none) and history."""

    provider = serializers.CharField()
    label = serializers.CharField()
    active = AIKeySerializer(allow_null=True)
    history = AIKeySerializer(many=True)


class NewKeySerializer(serializers.Serializer):
    """The key input. Write-only: the value is never returned."""

    provider = serializers.CharField(max_length=32)
    api_key = serializers.CharField(
        write_only=True, trim_whitespace=True, max_length=512, allow_blank=False
    )

    def validate(self, attrs: dict) -> dict:
        """Apply the service rules (registered provider, header-safe key)."""
        try:
            attrs["api_key"] = key_service.validate(attrs["provider"], attrs["api_key"])
        except key_service.InvalidKey as exc:
            raise serializers.ValidationError({"api_key": [str(exc)]}) from exc
        return attrs
