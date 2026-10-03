"""App configuration for :mod:`tripaulx.core`."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    """Core app: base models, tenant middleware, health checks, test helpers."""

    name = "tripaulx.core"
    label = "tpsdk_core"
    verbose_name = _("Core")
    default_auto_field = "django.db.models.BigAutoField"
