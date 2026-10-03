"""The user's trusted devices: list and revoke."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from ...services import trusted_devices
from ...services.errors import NotFound
from ..schema import untyped
from ..serializers import TrustedDeviceSerializer
from .base import AccountsAPIView, AccountsListAPIView


class TrustedDeviceListView(AccountsListAPIView):
    """Active trusted devices of the authenticated user."""

    permission_classes = [IsAuthenticated]
    serializer_class = TrustedDeviceSerializer

    def get_queryset(self) -> QuerySet:
        """Only the user's own active devices."""
        return trusted_devices.active_devices(self.request.user)


class TrustedDeviceDetailView(AccountsAPIView):
    """Revoke one trusted device (it will need the second factor again)."""

    permission_classes = [IsAuthenticated]

    @untyped
    def delete(self, request: Request, pk: Any) -> Response:
        """Revoke the device."""
        if not trusted_devices.revoke_device(request.user, pk):
            raise NotFound(_("Device not found."))
        return Response(status=status.HTTP_204_NO_CONTENT)
