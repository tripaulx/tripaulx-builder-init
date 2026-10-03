"""``key/``: provider API keys (state for members, changes for admins).

The value goes in once (POST, write-only) and never comes back. Every answer
is the same state: per provider, the active key (who added it, when) and the
history of closed keys. To change a key, add another one: it replaces the
previous key of that provider and leaves the trail. DELETE answers 200 with
the state, not 204: the UI shows "deleted by X at 14:08" from the server.
"""

from __future__ import annotations

from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from tripaulx.ai import providers
from tripaulx.ai.services import keys

from ..permissions import IsAdminOrReadOnly
from ..serializers import NewKeySerializer, ProviderKeyStateSerializer


def _state(provider: str) -> dict:
    return {
        "provider": provider,
        "label": providers.label_of(provider),
        "active": keys.active(provider),
        "history": keys.history(provider),
    }


class AIKeyView(APIView):
    """GET every provider's state; POST adds a key; DELETE closes one."""

    permission_classes = [IsAdminOrReadOnly]
    serializer_class = ProviderKeyStateSerializer

    def get(self, request: Request) -> Response:
        """Key state of every registered provider."""
        states = [_state(name) for name in providers.names()]
        return Response(ProviderKeyStateSerializer(states, many=True).data)

    def post(self, request: Request) -> Response:
        """Add the active key of ``provider`` (replacing the previous one)."""
        serializer = NewKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.validated_data["provider"]
        keys.add(provider, serializer.validated_data["api_key"], by=request.user)
        data = ProviderKeyStateSerializer(_state(provider)).data
        return Response(data, status=status.HTTP_201_CREATED)

    def delete(self, request: Request) -> Response:
        """Close the active key of ``?provider=`` (body ``provider`` also works)."""
        provider = request.query_params.get("provider") or request.data.get(
            "provider", ""
        )
        if providers.get_provider(provider) is None:
            return Response(
                {"provider": [_("Choose a registered provider.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        keys.delete(provider, by=request.user)
        return Response(ProviderKeyStateSerializer(_state(provider)).data)
