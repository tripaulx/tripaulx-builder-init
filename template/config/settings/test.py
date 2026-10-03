"""Settings for the automated test-suite."""

from .base import *  # noqa: F401, F403
from .base_parts.common import get_env

SECRET_KEY = "test-only"
ALLOWED_HOSTS = ["*"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
LOGGING = {"version": 1, "disable_existing_loggers": False}
TRIPAULX = {**TRIPAULX, "BASE_DOMAIN": get_env("APP_BASE_DOMAIN", "test.localhost")}  # noqa: F405
