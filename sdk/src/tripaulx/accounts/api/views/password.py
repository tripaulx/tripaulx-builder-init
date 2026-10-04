"""Password reset by e-mail code and password change."""

from __future__ import annotations

from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from ...services import identity, passwords, tokens
from ..serializers import (
    EmailSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
)
from .base import AccountsAPIView


class PasswordResetRequestView(AccountsAPIView):
    """E-mail a reset code (the answer never reveals whether it exists)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"
    serializer_class = EmailSerializer

    def post(self, request: Request) -> Response:
        """Send the code when the account exists."""
        passwords.issue_reset(self.validated(EmailSerializer)["email"])
        return Response({"detail": _("If the e-mail exists, we sent a recovery code.")})


class PasswordResetConfirmView(AccountsAPIView):
    """Check the code and set the new password; every session ends."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request: Request) -> Response:
        """Reset the password."""
        data = self.validated(PasswordResetConfirmSerializer)
        passwords.confirm_reset(
            data["email"], data["code"], data["password"], data["password_confirm"]
        )
        return Response({"detail": _("Password reset.")})


class PasswordChangeView(AccountsAPIView):
    """Change the password; other sessions end, this one gets new tokens."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"
    serializer_class = PasswordChangeSerializer

    def post(self, request: Request) -> Response:
        """Change the password and return a fresh token pair."""
        data = self.validated(PasswordChangeSerializer)
        passwords.change_password(
            request.user,
            data["current_password"],
            data["new_password"],
            data["new_password_confirm"],
        )
        return Response(
            {"detail": _("Password changed."), **tokens.tokens_for(request.user)}
        )


class PasswordRulesView(AccountsAPIView):
    """The active password rules, translated, for sign-up and reset forms."""

    permission_classes = [AllowAny]
    # Public and harmless: a stale token must never turn it into a 401.
    authentication_classes: list = []

    @extend_schema(
        operation_id="auth_password_rules",
        responses=inline_serializer(
            "PasswordRules",
            {"rules": serializers.ListField(child=serializers.CharField())},
        ),
    )
    def get(self, request: Request) -> Response:
        """Return ``{"rules": [...]}`` from ``AUTH_PASSWORD_VALIDATORS``."""
        return Response({"rules": identity.password_rules()})
