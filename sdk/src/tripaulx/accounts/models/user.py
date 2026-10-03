"""Abstract user model every project's concrete ``User`` inherits from.

The SDK cannot own the concrete model: ``AUTH_USER_MODEL`` must live in a
project app so each project can add fields and migrations of its own.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import UserManager
from .roles import ADMIN_ROLES, Role


class AbstractTripaulxUser(AbstractUser):
    """User identified by e-mail, with a workspace role and login flags."""

    username = None  # type: ignore[assignment]
    email = models.EmailField(_("e-mail address"), unique=True)
    email_verified = models.BooleanField(
        _("e-mail verified"),
        default=False,
        help_text=_("Confirmed through a verification code."),
    )
    password_login_disabled = models.BooleanField(
        _("passkey-only login"),
        default=False,
        help_text=_(
            "Disables e-mail and password login. Only applies while the user "
            "has at least one passkey."
        ),
    )
    role = models.CharField(
        _("role"), max_length=16, choices=Role.choices, default=Role.MEMBER
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        abstract = True
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self) -> str:
        return self.email

    @property
    def is_workspace_admin(self) -> bool:
        """Whether the user may manage the workspace (owner or admin)."""
        return self.is_active and self.role in ADMIN_ROLES
