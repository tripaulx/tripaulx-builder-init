"""App configuration for :mod:`tripaulx.tenants`."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TenantsConfig(AppConfig):
    """Workspace and domain models; lives only in the public schema."""

    name = "tripaulx.tenants"
    label = "tpsdk_tenants"
    verbose_name = _("Workspaces")
    default_auto_field = "django.db.models.BigAutoField"
