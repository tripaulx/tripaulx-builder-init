"""Login with e-mail and password, then the mandatory second factor."""

from __future__ import annotations

from django.utils.translation import gettext as _
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from ...services import login
from ..serializers import LoginSerializer, LoginVerifySerializer, TicketSerializer
from .base import AccountsAPIView, login_response


class LoginView(AccountsAPIView):
    """Check the password; answer with a second-factor challenge.

    ``mfa_method`` tells the client which code to ask for: ``totp`` when the
    authenticator app is active (no e-mail is sent), ``email`` otherwise. A
    valid ``device_token`` skips the second factor and returns the tokens.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"
    serializer_class = LoginSerializer

    def post(self, request: Request) -> Response:
        """Start a login."""
        data = self.validated(LoginSerializer)
        outcome = login.password_login(
            request, data["email"], data["password"], data["device_token"]
        )
        return login_response(outcome)


class LoginVerifyView(AccountsAPIView):
    """Finish the login with the ticket and a code.

    The same field accepts the app code, the e-mailed code or a recovery code.
    ``trust_device`` returns a ``device_token`` that skips the next 2FA.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"
    serializer_class = LoginVerifySerializer

    def post(self, request: Request) -> Response:
        """Check the second factor and return the tokens."""
        data = self.validated(LoginVerifySerializer)
        outcome = login.verify_second_factor(
            request,
            data["ticket"],
            data["code"],
            trust_device=data["trust_device"],
            device_label=data["device_label"],
        )
        return login_response(outcome)


class LoginResendView(AccountsAPIView):
    """Send a new e-mail code for a login ticket (same answer in every case)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"
    serializer_class = TicketSerializer

    def post(self, request: Request) -> Response:
        """Resend when allowed; never reveal anything about the account."""
        login.resend_code(self.validated(TicketSerializer)["ticket"])
        return Response({"detail": _("If the code expired, we sent a new one.")})
