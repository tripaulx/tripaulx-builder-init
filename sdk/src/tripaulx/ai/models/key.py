"""Provider API keys of the workspace: one row per key, with who and when.

At most one key is active **per provider** (a partial unique constraint). A
closed key (deleted or replaced) keeps its row for the audit trail, but its
encrypted token is wiped at once: a revoked key has no reason to stay in the
database. Encryption is :mod:`tripaulx.core.crypto` (Fernet).

This model does not inherit ``BaseModel``: closing a key is its own soft
state (``closed_at`` plus the reason), and the rows are an append-only log.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from tripaulx.core import crypto

from .choices import KeyClosedReason


class AIKeyQuerySet(models.QuerySet):
    """Queries of the key table."""

    def active(self) -> AIKeyQuerySet:
        """Keys that were not closed."""
        return self.filter(closed_at__isnull=True)

    def active_for(self, provider: str) -> AIKey | None:
        """Return the key in use for ``provider``, or ``None``."""
        return self.active().filter(provider=provider).order_by("-created_at").first()


def _actor(verbose_name: str) -> models.ForeignKey:
    """Build a nullable link to the user who acted (the label survives it)."""
    return models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=verbose_name,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )


class AIKey(models.Model):
    """One API key of one provider: who added it, who closed it, and when."""

    provider = models.CharField(_("provider"), max_length=32, db_index=True)
    api_key_encrypted = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(_("added at"), auto_now_add=True)
    created_by = _actor(_("added by"))
    # The actor's name frozen at the time: the foreign key answers "who"
    # while the user exists, the label answers it afterwards.
    created_by_label = models.CharField(
        _("added by (name)"), max_length=254, blank=True, default=""
    )
    closed_at = models.DateTimeField(_("closed at"), null=True, blank=True)
    closed_by = _actor(_("closed by"))
    closed_by_label = models.CharField(
        _("closed by (name)"), max_length=254, blank=True, default=""
    )
    closed_reason = models.CharField(
        _("reason"),
        max_length=16,
        choices=KeyClosedReason.choices,
        blank=True,
        default="",
    )

    objects = AIKeyQuerySet.as_manager()

    class Meta:
        verbose_name = _("AI API key")
        verbose_name_plural = _("AI API keys")
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider"],
                condition=Q(closed_at__isnull=True),
                name="tpsdk_ai_one_active_key_per_provider",
            ),
        ]

    def __str__(self) -> str:
        state = _("active") if self.is_active else self.get_closed_reason_display()
        return f"{self.provider} · {state} · {self.created_at:%Y-%m-%d}"

    @property
    def is_active(self) -> bool:
        """Whether the key was not closed."""
        return self.closed_at is None

    @property
    def api_key(self) -> str:
        """The decrypted key (empty when closed or unreadable)."""
        return crypto.decrypt(self.api_key_encrypted)

    @property
    def readable(self) -> bool:
        """Whether a token is stored and decrypts with the current key.

        A token that no longer decrypts (field key rotated without
        re-encrypting) is not a configured key, and the UI must say so.
        """
        return bool(self.api_key)
