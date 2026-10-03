"""One-time numeric codes sent by e-mail (stored as a hash only)."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tripaulx.core.models import BaseModel


class EmailCodePurpose(models.TextChoices):
    """What an e-mail code (or e-mail template) is for."""

    EMAIL_VERIFY = "email_verify", _("E-mail verification")
    LOGIN_2FA = "login_2fa", _("Two-step verification")
    PASSWORD_RESET = "password_reset", _("Password reset")
    INVITE = "invite", _("Workspace invitation")


class EmailCode(BaseModel):
    """A 6-digit code with expiry and an attempt limit.

    Issuing a new code consumes the previous active ones of the same purpose.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_codes",
        verbose_name=_("user"),
    )
    purpose = models.CharField(
        _("purpose"), max_length=32, choices=EmailCodePurpose.choices
    )
    code_hash = models.CharField(_("code hash"), max_length=128)
    expires_at = models.DateTimeField(_("expires at"))
    attempts = models.PositiveSmallIntegerField(_("attempts"), default=0)
    consumed_at = models.DateTimeField(_("consumed at"), null=True, blank=True)

    class Meta:
        verbose_name = _("e-mail code")
        verbose_name_plural = _("e-mail codes")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "purpose"])]

    def __str__(self) -> str:
        return f"{self.get_purpose_display()} · {self.user_id}"

    @property
    def is_expired(self) -> bool:
        """Whether the code is past its expiry."""
        return timezone.now() >= self.expires_at
