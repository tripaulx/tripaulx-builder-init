"""App configuration for :mod:`tripaulx.mail`."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MailConfig(AppConfig):
    """E-mail configuration; installed in the public schema only."""

    name = "tripaulx.mail"
    label = "tpsdk_mail"
    verbose_name = _("E-mail")
    default_auto_field = "django.db.models.BigAutoField"
