"""DRF permission of the restricted legal area."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from ..services import can_read_restricted


class LegalAccessPermission(BasePermission):
    """Allow the users of :func:`~tripaulx.legal.services.can_read_restricted`."""

    message = _("The legal area is restricted to authorized users.")

    def has_permission(self, request: Request, view: Any) -> bool:
        """Apply the access rule of the restricted documents."""
        return can_read_restricted(request.user)
