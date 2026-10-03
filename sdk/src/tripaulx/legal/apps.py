"""App configuration for :mod:`tripaulx.legal`."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LegalConfig(AppConfig):
    """Legal documents read from files; the app has no models."""

    name = "tripaulx.legal"
    label = "tpsdk_legal"
    verbose_name = _("Legal and governance")
    default_auto_field = "django.db.models.BigAutoField"
