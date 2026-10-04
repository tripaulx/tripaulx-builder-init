"""Input serializers of login, codes and passwords.

Password strength is checked by the services (one rule, one place), so the
serializers only check shapes.
"""

from __future__ import annotations

from rest_framework import serializers


class EmailSerializer(serializers.Serializer):
    """Just an e-mail address."""

    email = serializers.EmailField()


class EmailCodeSerializer(serializers.Serializer):
    """An e-mail address and the code sent to it."""

    email = serializers.EmailField()
    code = serializers.CharField(min_length=4, max_length=12)


class LoginSerializer(serializers.Serializer):
    """E-mail, password and an optional trusted-device token."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    device_token = serializers.CharField(required=False, allow_blank=True, default="")


class LoginVerifySerializer(serializers.Serializer):
    """Second factor: app or e-mail code, or a recovery code (longer)."""

    ticket = serializers.CharField()
    code = serializers.CharField(min_length=4, max_length=24)
    trust_device = serializers.BooleanField(required=False, default=False)
    device_label = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=120
    )


class TicketSerializer(serializers.Serializer):
    """The login ticket alone (resend)."""

    ticket = serializers.CharField(required=False, allow_blank=True, default="")


class CodeSerializer(serializers.Serializer):
    """An authenticator code or, where accepted, a recovery code."""

    code = serializers.CharField(min_length=4, max_length=24)


class RecoveryCodesSerializer(serializers.Serializer):
    """How many recovery codes to generate."""

    quantity = serializers.IntegerField(
        required=False, default=None, min_value=1, max_value=20
    )


class PasswordResetConfirmSerializer(serializers.Serializer):
    """E-mail, reset code and the new password."""

    email = serializers.EmailField()
    code = serializers.CharField(min_length=4, max_length=12)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordChangeSerializer(serializers.Serializer):
    """Current and new password of the logged-in user."""

    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)


class RefreshSerializer(serializers.Serializer):
    """A refresh token (logout)."""

    refresh = serializers.CharField(required=False, allow_blank=True, default="")
