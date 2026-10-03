"""Roles of a user inside their workspace."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    """Workspace roles, from most to least privileged."""

    OWNER = "owner", _("Owner")
    ADMIN = "admin", _("Admin")
    MEMBER = "member", _("Member")


ADMIN_ROLES = frozenset({Role.OWNER, Role.ADMIN})
