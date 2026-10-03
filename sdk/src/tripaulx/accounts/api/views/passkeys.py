"""Passkey management (authenticated) and passkey login (anonymous).

Every service call takes the request: the RP ID and accepted origin come
from the request host (see ``services.passkeys.relying_party``).
"""

from __future__ import annotations

import json
from typing import Any

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from ...services import login, passkeys
from ..schema import untyped
from ..serializers import (
    PasskeyLoginBeginSerializer,
    PasskeyLoginCompleteSerializer,
    PasskeyRegisterSerializer,
    PasskeySerializer,
    PasswordLoginToggleSerializer,
    UserSerializer,
)
from .base import AccountsAPIView, login_response


def passkey_list(user: Any) -> dict[str, Any]:
    """Return the user's passkeys, as list and register answer them."""
    return {"passkeys": PasskeySerializer(user.passkeys.all(), many=True).data}


class PasskeyRegisterBeginView(AccountsAPIView):
    """Registration options for the authenticated user."""

    permission_classes = [IsAuthenticated]

    @untyped
    def post(self, request: Request) -> Response:
        """Return the options and remember the challenge."""
        return Response(passkeys.registration_options(request.user, request))


class PasskeyRegisterCompleteView(AccountsAPIView):
    """Verify and store a new passkey."""

    permission_classes = [IsAuthenticated]
    serializer_class = PasskeyRegisterSerializer

    def post(self, request: Request) -> Response:
        """Register and return the updated list."""
        data = self.validated(PasskeyRegisterSerializer)
        passkeys.verify_registration(
            request.user,
            json.dumps(data["credential"]),
            data["name"] or "Passkey",
            request=request,
        )
        return Response(passkey_list(request.user), status=status.HTTP_201_CREATED)


class PasskeyListView(AccountsAPIView):
    """The user's passkeys."""

    permission_classes = [IsAuthenticated]

    @untyped
    def get(self, request: Request) -> Response:
        """List them."""
        return Response(passkey_list(request.user))


class PasskeyDetailView(AccountsAPIView):
    """Rename (PATCH) or remove (DELETE) one of the user's passkeys."""

    permission_classes = [IsAuthenticated]
    serializer_class = PasskeySerializer

    def patch(self, request: Request, pk: Any) -> Response:
        """Rename the passkey."""
        name = self.validated(PasskeySerializer).get("name", "")
        passkey = passkeys.rename_passkey(request.user, pk, name)
        return Response(PasskeySerializer(passkey).data)

    def delete(self, request: Request, pk: Any) -> Response:
        """Remove it, except the last one while password login is off."""
        passkeys.delete_passkey(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordLoginToggleView(AccountsAPIView):
    """Turn e-mail and password login off (passkey-only) or back on."""

    permission_classes = [IsAuthenticated]
    serializer_class = PasswordLoginToggleSerializer

    def post(self, request: Request) -> Response:
        """Apply the choice and return the user, like ``/me/``."""
        disabled = self.validated(PasswordLoginToggleSerializer)["disabled"]
        passkeys.set_password_login_disabled(request.user, disabled)
        return Response(UserSerializer(request.user).data)


class PasskeyLoginBeginView(AccountsAPIView):
    """Authentication options, with or without an e-mail."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"
    serializer_class = PasskeyLoginBeginSerializer

    def post(self, request: Request) -> Response:
        """Return a ticket and the options."""
        email = self.validated(PasskeyLoginBeginSerializer)["email"]
        ticket, options = login.passkey_begin(request, email)
        return Response({"ticket": ticket, "options": options})


class PasskeyLoginCompleteView(AccountsAPIView):
    """Verify the passkey assertion and return the tokens."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"
    serializer_class = PasskeyLoginCompleteSerializer

    def post(self, request: Request) -> Response:
        """Log in with the passkey."""
        data = self.validated(PasskeyLoginCompleteSerializer)
        outcome = login.passkey_login(
            request, data["ticket"], json.dumps(data["credential"])
        )
        return login_response(outcome)
