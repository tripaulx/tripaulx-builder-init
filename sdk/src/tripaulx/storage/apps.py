"""App configuration for :mod:`tripaulx.storage`."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StorageConfig(AppConfig):
    """Access to the private bucket; the app has no models."""

    name = "tripaulx.storage"
    label = "tpsdk_storage"
    verbose_name = _("Object storage")
    default_auto_field = "django.db.models.BigAutoField"
