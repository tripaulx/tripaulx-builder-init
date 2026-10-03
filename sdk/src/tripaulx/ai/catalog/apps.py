"""App configuration for :mod:`tripaulx.ai.catalog`."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AICatalogConfig(AppConfig):
    """The model catalog; installed in the public schema only."""

    name = "tripaulx.ai.catalog"
    label = "tpsdk_ai_catalog"
    verbose_name = _("AI model catalog")
    default_auto_field = "django.db.models.BigAutoField"
