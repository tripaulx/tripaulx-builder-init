"""The authenticator app (TOTP, RFC 6238) of a user, one per account."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from tripaulx.core import crypto
from tripaulx.core.models import BaseModel


class TotpDevice(BaseModel):
    """TOTP secret (encrypted) and its confirmation and anti-replay state.

    - The secret is **encrypted**, not hashed: it must be read back at every
      login, and whoever holds it can generate valid codes.
    - The device is born *pending* (``confirmed_at`` empty) when the QR code
      is shown, and only counts at login after the user types a valid code.
    - ``last_step`` is the anti-replay guard: a code accepted for a 30-second
      step (or an older one) is never accepted again.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="totp_device",
        verbose_name=_("user"),
    )
    secret_encrypted = models.TextField(_("encrypted secret"))
    confirmed_at = models.DateTimeField(_("confirmed at"), null=True, blank=True)
    last_used_at = models.DateTimeField(_("last used at"), null=True, blank=True)
    last_step = models.BigIntegerField(_("last accepted step"), default=0)

    class Meta:
        verbose_name = _("authenticator app")
        verbose_name_plural = _("authenticator apps")

    def __str__(self) -> str:
        return str(self.user_id)

    @property
    def confirmed(self) -> bool:
        """Whether the device was confirmed with a first valid code."""
        return self.confirmed_at is not None

    @property
    def secret(self) -> str:
        """The base32 secret, decrypted (empty when unreadable)."""
        return crypto.decrypt(self.secret_encrypted)
