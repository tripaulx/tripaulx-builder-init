"""Second-factor settings: recovery codes and the authenticator app.

Endpoints that take a 6-digit code use the ``auth_otp`` bucket: there are a
million possible codes and the throttle is what stops trying them all.
"""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from ...services import recovery_codes, totp
from ..schema import untyped
from ..serializers import CodeSerializer, RecoveryCodesSerializer
from .base import AccountsAPIView


def totp_status(user: Any) -> dict[str, Any]:
    """Whether the app is active, since when, and the codes left."""
    device = totp.confirmed_device(user)
    return {
        "enabled": device is not None,
        "confirmed_at": device.confirmed_at if device else None,
        "recovery_codes_remaining": recovery_codes.remaining(user),
    }


class RecoveryCodesView(AccountsAPIView):
    """Count (GET) or regenerate (POST) the recovery codes.

    POST returns the codes in plain text, the only time they are shown, and
    invalidates the previous list.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = RecoveryCodesSerializer

    def get(self, request: Request) -> Response:
        """Return how many codes are left."""
        return Response({"remaining": recovery_codes.remaining(request.user)})

    def post(self, request: Request) -> Response:
        """Generate a new list."""
        quantity = self.validated(RecoveryCodesSerializer)["quantity"]
        codes = recovery_codes.generate_codes(request.user, quantity)
        return Response(
            {"codes": codes, "remaining": len(codes)}, status=status.HTTP_201_CREATED
        )


class TotpStatusView(AccountsAPIView):
    """Status of the authenticator app."""

    permission_classes = [IsAuthenticated]

    @untyped
    def get(self, request: Request) -> Response:
        """Return the status (never the secret)."""
        return Response(totp_status(request.user))


class TotpSetupView(AccountsAPIView):
    """Start (POST) or cancel (DELETE) the app setup.

    The secret is returned here and only here: there is no GET for it.
    """

    permission_classes = [IsAuthenticated]

    @untyped
    def post(self, request: Request) -> Response:
        """Return the secret, the ``otpauth://`` URI and the QR code (SVG)."""
        device = totp.begin_setup(request.user)
        uri = totp.provisioning_uri(device.secret, request.user.email, totp.issuer())
        return Response(
            {"secret": device.secret, "otpauth_uri": uri, "qr_svg": totp.qr_svg(uri)}
        )

    @untyped
    def delete(self, request: Request) -> Response:
        """Drop a pending setup (an active app is untouched)."""
        totp.cancel_setup(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TotpConfirmView(AccountsAPIView):
    """Confirm the app with its first code and hand out recovery codes."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"
    serializer_class = CodeSerializer

    def post(self, request: Request) -> Response:
        """Activate the app; the new recovery codes are shown once."""
        totp.confirm_setup(request.user, self.validated(CodeSerializer)["code"])
        codes = recovery_codes.generate_codes(request.user)
        return Response(
            {**totp_status(request.user), "recovery_codes": codes},
            status=status.HTTP_201_CREATED,
        )


class TotpDisableView(AccountsAPIView):
    """Turn the app off with an app code or a recovery code."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_otp"
    serializer_class = CodeSerializer

    def post(self, request: Request) -> Response:
        """Disable the app; the login falls back to e-mail codes."""
        totp.disable(request.user, self.validated(CodeSerializer)["code"])
        return Response(totp_status(request.user))
