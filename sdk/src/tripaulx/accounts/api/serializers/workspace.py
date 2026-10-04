"""Serializers of signup and invitations."""

from __future__ import annotations

from rest_framework import serializers

from ...models import Invitation, Role


class SignupSerializer(serializers.Serializer):
    """Owner's name and credentials, and the new workspace (optional slug)."""

    email = serializers.EmailField()
    # Blank passes here so the service answers with ``field: "full_name"``.
    full_name = serializers.CharField(max_length=301, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    workspace_name = serializers.CharField(max_length=100)
    slug = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=30
    )


class InvitationSerializer(serializers.ModelSerializer):
    """An invitation as listed to workspace admins (never the token)."""

    invited_by = serializers.EmailField(source="invited_by.email", read_only=True)
    is_pending = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invitation
        fields = [
            "id",
            "email",
            "role",
            "invited_by",
            "created_at",
            "expires_at",
            "is_pending",
        ]
        read_only_fields = fields


class InvitationCreateSerializer(serializers.Serializer):
    """Who to invite and with which role."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=Role.choices, default=Role.MEMBER)


class InvitationAcceptSerializer(serializers.Serializer):
    """The token from the e-mailed link and the new account's password."""

    token = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    full_name = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=301
    )
    first_name = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=150
    )
    last_name = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=150
    )
