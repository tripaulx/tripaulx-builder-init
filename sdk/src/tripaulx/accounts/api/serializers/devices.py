"""Serializers of passkeys and trusted devices."""

from __future__ import annotations

from rest_framework import serializers

from ...models import TrustedDevice, WebAuthnCredential


class PasskeySerializer(serializers.ModelSerializer):
    """A passkey as listed to its owner; ``name`` is the only editable field."""

    class Meta:
        model = WebAuthnCredential
        fields = ["id", "name", "created_at", "last_used_at"]
        read_only_fields = ["id", "created_at", "last_used_at"]


DEFAULT_PASSKEY_NAME = "Passkey"


class PasskeyRegisterSerializer(serializers.Serializer):
    """The browser's registration response and a name for the passkey."""

    credential = serializers.JSONField()
    name = serializers.CharField(
        required=False, allow_blank=True, default=DEFAULT_PASSKEY_NAME, max_length=120
    )


class PasswordLoginToggleSerializer(serializers.Serializer):
    """``disabled=True`` closes e-mail and password login."""

    disabled = serializers.BooleanField()


class PasskeyLoginBeginSerializer(serializers.Serializer):
    """Optional e-mail; without it any passkey of the workspace may answer."""

    email = serializers.EmailField(required=False, allow_blank=True, default="")


class PasskeyLoginCompleteSerializer(serializers.Serializer):
    """The ticket from "begin" and the browser's assertion."""

    ticket = serializers.CharField()
    credential = serializers.JSONField()


class TrustedDeviceSerializer(serializers.ModelSerializer):
    """A trusted device as listed to its owner (never the token)."""

    class Meta:
        model = TrustedDevice
        fields = [
            "id",
            "device_label",
            "ip_address",
            "user_agent",
            "created_at",
            "last_used_at",
            "expires_at",
        ]
        read_only_fields = fields
