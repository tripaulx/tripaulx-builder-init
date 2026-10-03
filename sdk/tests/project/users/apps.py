"""App configuration of the test users app."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Test users app."""

    name = "tests.project.users"
    label = "users"
    default_auto_field = "django.db.models.BigAutoField"
