"""Passkeys (WebAuthn / FIDO2 credentials).

The WebAuthn challenge lives in the Django cache, not in the database.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from tripaulx.core.models import BaseModel


class WebAuthnCredential(BaseModel):
    """A passkey registered by a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="passkeys",
        verbose_name=_("user"),
    )
    # Both stored as base64url.
    credential_id = models.CharField(_("credential ID"), max_length=400, unique=True)
    public_key = models.TextField(_("public key"))
    sign_count = models.BigIntegerField(_("signature counter"), default=0)
    transports = models.JSONField(_("transports"), default=list, blank=True)
    aaguid = models.CharField(_("AAGUID"), max_length=64, blank=True)
    name = models.CharField(_("name"), max_length=120, default="Passkey")
    last_used_at = models.DateTimeField(_("last used at"), null=True, blank=True)

    class Meta:
        verbose_name = _("passkey")
        verbose_name_plural = _("passkeys")
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.name} · {self.user_id}"
