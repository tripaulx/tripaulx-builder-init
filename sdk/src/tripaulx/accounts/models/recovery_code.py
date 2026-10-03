"""Single-use recovery codes: the way in when the second factor is lost."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from tripaulx.core.models import BaseModel


class RecoveryCode(BaseModel):
    """A recovery code; only its hash is stored.

    The plain text exists once, when the list is generated. Each code
    completes exactly one login (or disables the authenticator app).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recovery_codes",
        verbose_name=_("user"),
    )
    code_hash = models.CharField(_("code hash"), max_length=128)
    # First characters in clear text: they tell which code of the printed list
    # was used without making it guessable.
    prefix = models.CharField(_("prefix"), max_length=8, blank=True)
    label = models.CharField(_("label"), max_length=120, blank=True)
    used_at = models.DateTimeField(_("used at"), null=True, blank=True)

    class Meta:
        verbose_name = _("recovery code")
        verbose_name_plural = _("recovery codes")
        ordering = ("created_at",)
        indexes = [models.Index(fields=["user", "used_at"])]

    def __str__(self) -> str:
        return f"{self.prefix}… · {self.user_id}"

    @property
    def is_used(self) -> bool:
        """Whether the code was already used."""
        return self.used_at is not None
