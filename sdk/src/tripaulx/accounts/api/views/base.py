"""Base view and response helpers shared by the accounts API."""

from __future__ import annotations

from typing import Any

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from ...services.errors import AccountsError
from ...services.login import LoginOutcome
from ..serializers import UserSerializer


class AccountsErrorMixin:
    """Turn any :class:`AccountsError` into ``{"detail": ..., **extra}``."""

    def handle_exception(self, exc: Exception) -> Response:
        """Answer service errors with their own status and message."""
        if isinstance(exc, AccountsError):
            body = {"detail": exc.message, **exc.extra}
            return Response(body, status=exc.status_code)
        return super().handle_exception(exc)  # type: ignore[misc]

    def validated(self, serializer_class: type[Serializer]) -> dict[str, Any]:
        """Validate ``request.data`` with ``serializer_class`` (400 on error)."""
        serializer = serializer_class(data=self.request.data)  # type: ignore[attr-defined]
        serializer.is_valid(raise_exception=True)
        return dict(serializer.validated_data)


class AccountsAPIView(AccountsErrorMixin, APIView):
    """``APIView`` with the accounts error handling."""


class AccountsListAPIView(AccountsErrorMixin, generics.ListAPIView):
    """``ListAPIView`` with the accounts error handling."""


def session_payload(outcome: LoginOutcome) -> dict[str, Any]:
    """Body of a completed login: tokens, the user and any extras."""
    return {
        **(outcome.tokens or {}),
        "user": UserSerializer(outcome.user).data,
        **outcome.extra,
    }


def login_response(outcome: LoginOutcome) -> Response:
    """Answer a login step: the challenge, or the completed session."""
    if outcome.challenge is not None:
        return Response(outcome.challenge)
    return Response(session_payload(outcome))
