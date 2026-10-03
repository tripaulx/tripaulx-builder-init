"""Permissions of the AI API: members read, owners and admins write.

Running an agent is NOT covered here: any member may run one, limited by the
``ai_run`` throttle and the daily cap.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from tripaulx.accounts.api.permissions import IsWorkspaceAdmin


def is_admin(request: Request) -> bool:
    """Whether the request user is an owner or admin of the workspace."""
    return IsWorkspaceAdmin().has_permission(request, None)


class IsAdminOrReadOnly(BasePermission):
    """Any authenticated member reads; only owners and admins write."""

    message = _("Only workspace owners and admins can change this.")

    def has_permission(self, request: Request, view: Any) -> bool:
        """Safe methods for members, the rest for admins."""
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or is_admin(request)
