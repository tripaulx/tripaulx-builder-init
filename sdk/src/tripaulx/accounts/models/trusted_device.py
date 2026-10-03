"""Browsers trusted to skip the second factor at login."""

from __future__ import annotations

import hashlib

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tripaulx.core.models import BaseModel


class TrustedDevice(BaseModel):
    """A trusted device; only the sha256 of its token is stored.

    The raw token lives only on the client. A user may trust several
    devices (one per browser).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trusted_devices",
        verbose_name=_("user"),
    )
    token_hash = models.CharField(_("token hash"), max_length=64, unique=True)
    device_label = models.CharField(_("device label"), max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.TextField(_("user agent"), blank=True)
    expires_at = models.DateTimeField(_("expires at"), db_index=True)
    last_used_at = models.DateTimeField(_("last used at"), null=True, blank=True)
    is_active = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        verbose_name = _("trusted device")
        verbose_name_plural = _("trusted devices")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "is_active"])]

    def __str__(self) -> str:
        return f"{self.device_label or self.pk} · {self.user_id}"

    @property
    def is_valid(self) -> bool:
        """Active and not expired."""
        return self.is_active and timezone.now() < self.expires_at

    @staticmethod
    def hash_token(token: str) -> str:
        """Return the sha256 (hex) of a raw token, used as the lookup key."""
        return hashlib.sha256(token.encode()).hexdigest()
