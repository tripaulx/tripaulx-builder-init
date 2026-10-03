"""Session endpoints: refresh, logout and the current user."""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView as BaseRefreshView

from ...services.tokens import TenantRefreshToken
from ..serializers import RefreshSerializer, UserSerializer
from .base import AccountsAPIView


class TenantTokenRefreshSerializer(TokenRefreshSerializer):
    """Refresh bound to the workspace that issued the token.

    The route is anonymous (the refresh token *is* the credential), so it
    never passes through ``TenantJWTAuthentication``: without this token
    class, a refresh token from another workspace would buy a valid access
    token here.
    """

    token_class = TenantRefreshToken


class TokenRefreshView(BaseRefreshView):
    """Refresh the access token, with its own throttle bucket.

    In the shared ``anon`` bucket, many users behind one IP would exhaust it
    and the refresh would start failing for people simply working.
    """

    serializer_class = TenantTokenRefreshSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_refresh"


class LogoutView(AccountsAPIView):
    """Blacklist the refresh token; leaving always "works"."""

    permission_classes = [IsAuthenticated]
    serializer_class = RefreshSerializer

    def post(self, request: Request) -> Response:
        """Blacklist the given refresh token, ignoring bad ones."""
        token = self.validated(RefreshSerializer)["refresh"]
        if token:
            try:
                TenantRefreshToken(token).blacklist()
            except (TokenError, InvalidToken):
                pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(AccountsAPIView):
    """The authenticated user."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request: Request) -> Response:
        """Return the current user."""
        return Response(UserSerializer(request.user).data)
