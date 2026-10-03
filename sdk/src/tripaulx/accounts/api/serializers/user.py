"""Serializers of the current user and of workspace members."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from ...models import Role
from ...services.login.second_factor import needs_strong_factor


class UserSerializer(serializers.ModelSerializer):
    """The authenticated user, as returned by login and ``/me/``."""

    is_workspace_admin = serializers.BooleanField(read_only=True)
    mfa_setup_required = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_workspace_admin",
            "email_verified",
            "password_login_disabled",
            "is_staff",
            "mfa_setup_required",
        ]
        read_only_fields = fields

    def get_mfa_setup_required(self, user: Any) -> bool:
        """Privileged account still relying on the e-mail second factor."""
        return needs_strong_factor(user)


class MemberSerializer(serializers.ModelSerializer):
    """A member as listed to workspace admins."""

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "email_verified",
            "date_joined",
            "last_login",
        ]
        read_only_fields = fields


class MemberRoleSerializer(serializers.Serializer):
    """New role of a member."""

    role = serializers.ChoiceField(choices=Role.choices)
