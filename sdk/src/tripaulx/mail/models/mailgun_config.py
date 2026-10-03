"""Global Mailgun configuration (a singleton in the public schema).

The API key is never stored in clear text: only the Fernet token in
``api_key_encrypted`` reaches the database, and :attr:`MailgunConfig.api_key`
encrypts and decrypts it through :mod:`tripaulx.core.crypto`.

This model does not inherit ``BaseModel`` on purpose: it is a singleton with
the fixed primary key ``1``, and soft delete makes no sense for it.
"""

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_tenants.utils import get_public_schema_name, schema_context

from tripaulx.core import crypto

SINGLETON_PK = 1


class MailgunRegion(models.TextChoices):
    """Mailgun API regions."""

    US = "us", _("United States")
    EU = "eu", _("Europe")


class MailgunConfig(models.Model):
    """Mailgun credentials and sender shared by every workspace."""

    enabled = models.BooleanField(
        _("enabled"), default=False, help_text=_("Send e-mail through Mailgun.")
    )
    api_key_encrypted = models.TextField(_("encrypted API key"), blank=True)
    domain = models.CharField(
        _("sending domain"),
        max_length=200,
        blank=True,
        help_text=_("For example: mg.example.com"),
    )
    region = models.CharField(
        _("region"), max_length=2, choices=MailgunRegion.choices, default="us"
    )
    default_from_email = models.EmailField(_("default sender address"), blank=True)
    default_from_name = models.CharField(
        _("default sender name"), max_length=120, blank=True
    )
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("e-mail configuration (Mailgun)")
        verbose_name_plural = _("e-mail configuration (Mailgun)")

    def __str__(self) -> str:
        return str(_("E-mail configuration (Mailgun)"))

    @property
    def api_key(self) -> str:
        """The decrypted API key (empty when not configured)."""
        return crypto.decrypt(self.api_key_encrypted)

    @api_key.setter
    def api_key(self, value: str) -> None:
        self.api_key_encrypted = crypto.encrypt(value or "")

    @property
    def base_url(self) -> str:
        """The API endpoint of the configured region."""
        if self.region == MailgunRegion.EU:
            return "https://api.eu.mailgun.net/v3"
        return "https://api.mailgun.net/v3"

    @property
    def is_ready(self) -> bool:
        """Whether everything needed to send is set: enabled, key and domain."""
        return self.enabled and bool(self.domain) and bool(self.api_key)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Force the singleton primary key; always write to the public schema."""
        self.pk = SINGLETON_PK
        with schema_context(get_public_schema_name()):
            super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> MailgunConfig:
        """Return the singleton, creating it, always from the public schema."""
        with schema_context(get_public_schema_name()):
            obj, _created = cls.objects.get_or_create(pk=SINGLETON_PK)
        return obj
