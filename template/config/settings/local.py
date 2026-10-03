"""Local development settings."""

from tripaulx.settings.security import allowed_hosts

from .base import *  # noqa: F401, F403
from .base_parts.common import get_env, get_env_bool, get_env_list
from .base_parts.tripaulx import TRIPAULX

SECRET_KEY = get_env("SECRET_KEY", "dev-only-not-for-production")
DEBUG = get_env_bool("DEBUG", default=True)

ALLOWED_HOSTS = allowed_hosts(
    TRIPAULX["BASE_DOMAIN"], "localhost", "127.0.0.1", *get_env_list("ALLOWED_HOSTS")
)
CSRF_TRUSTED_ORIGINS = [
    f"http://*.{TRIPAULX['BASE_DOMAIN']}:8000",
    f"http://{TRIPAULX['BASE_DOMAIN']}:8000",
]

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
# Any local frontend may call the API (it authenticates with bearer JWTs).
CORS_ALLOW_ALL_ORIGINS = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "local-development",
    }
}
