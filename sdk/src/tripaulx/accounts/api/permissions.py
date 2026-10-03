"""DRF permissions based on the workspace role."""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class IsWorkspaceAdmin(BasePermission):
    """Allow active owners and admins of the current workspace."""

    def has_permission(self, request: Request, view: Any) -> bool:
        """Check ``user.is_workspace_admin``."""
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "is_workspace_admin", False)
        )
