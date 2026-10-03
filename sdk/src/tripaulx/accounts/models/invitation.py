"""Invitations to join a workspace, accepted with a single-use token."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tripaulx.core.models import BaseModel

from .roles import Role


class Invitation(BaseModel):
    """An e-mail invitation; only the sha256 of its token is stored.

    Revoking an invitation soft-deletes it.
    """

    email = models.EmailField(_("e-mail address"))
    role = models.CharField(
        _("role"), max_length=16, choices=Role.choices, default=Role.MEMBER
    )
    token_hash = models.CharField(_("token hash"), max_length=64, unique=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("invited by"),
    )
    expires_at = models.DateTimeField(_("expires at"))
    accepted_at = models.DateTimeField(_("accepted at"), null=True, blank=True)

    class Meta:
        verbose_name = _("invitation")
        verbose_name_plural = _("invitations")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["email", "accepted_at"])]

    def __str__(self) -> str:
        return self.email

    @property
    def is_pending(self) -> bool:
        """Not accepted, not revoked and not expired."""
        return (
            self.accepted_at is None
            and self.deleted_at is None
            and timezone.now() < self.expires_at
        )
