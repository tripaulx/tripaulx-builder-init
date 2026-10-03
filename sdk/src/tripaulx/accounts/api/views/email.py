"""E-mail verification by code."""

from __future__ import annotations

from django.utils.translation import gettext as _
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from ...services import login, verification
from ..serializers import EmailCodeSerializer, EmailSerializer
from .base import AccountsAPIView, login_response


class EmailVerifyView(AccountsAPIView):
    """Confirm the e-mail with its code and log in (the code is the factor)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"
    serializer_class = EmailCodeSerializer

    def post(self, request: Request) -> Response:
        """Verify and return the tokens."""
        data = self.validated(EmailCodeSerializer)
        user = verification.verify_email(data["email"], data["code"])
        return login_response(login.complete_login(user, request, "email_verify"))


class EmailResendView(AccountsAPIView):
    """Resend the verification code of a pending account (always silent)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"
    serializer_class = EmailSerializer

    def post(self, request: Request) -> Response:
        """Resend when allowed."""
        verification.resend_verification(self.validated(EmailSerializer)["email"])
        return Response(
            {"detail": _("If there is a pending account, we sent a new code.")}
        )
