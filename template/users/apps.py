"""App configuration of the users app."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    """Users app; installed in the public schema and in every workspace."""

    name = "users"
    verbose_name = _("Users")
    default_auto_field = "django.db.models.BigAutoField"
