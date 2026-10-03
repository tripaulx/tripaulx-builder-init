"""App configuration for :mod:`tripaulx.accounts`."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    """Account security; installed in every schema next to the user model."""

    name = "tripaulx.accounts"
    label = "tpsdk_accounts"
    verbose_name = _("Accounts")
    default_auto_field = "django.db.models.BigAutoField"
