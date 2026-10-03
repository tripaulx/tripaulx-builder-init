"""App configuration for :mod:`tripaulx.ai`."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AIConfig(AppConfig):
    """Per-workspace AI: settings, keys, agents, skills and events."""

    name = "tripaulx.ai"
    label = "tpsdk_ai"
    verbose_name = _("Artificial intelligence")
    default_auto_field = "django.db.models.BigAutoField"
