"""Settings for the automated test-suite."""

from .base import *  # noqa: F401, F403
from .base_parts.common import get_env

# Long enough for HS256 (SimpleJWT signs with SECRET_KEY by default).
SECRET_KEY = "test-only-insecure-secret-key-0123456789abcdef"
ALLOWED_HOSTS = ["*"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
LOGGING = {"version": 1, "disable_existing_loggers": False}
TRIPAULX = {**TRIPAULX, "BASE_DOMAIN": get_env("APP_BASE_DOMAIN", "test.localhost")}  # noqa: F405
