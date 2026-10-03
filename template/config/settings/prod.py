"""Production settings (CapRover). Fails fast on unsafe configuration."""

from tripaulx.settings.security import allowed_hosts, https_origins

from .base import *  # noqa: F401, F403
from .base_parts.common import get_env, get_env_bool, get_env_list
from .base_parts.tripaulx import TRIPAULX

SECRET_KEY = get_env("SECRET_KEY", required=True)

DEBUG = get_env_bool("DEBUG", default=False)
if DEBUG:
    raise RuntimeError("DEBUG=True is not allowed in production.")

ALLOWED_HOSTS = allowed_hosts(TRIPAULX["BASE_DOMAIN"], *get_env_list("ALLOWED_HOSTS"))
CSRF_TRUSTED_ORIGINS = get_env_list(
    "CSRF_TRUSTED_ORIGINS", default=https_origins(ALLOWED_HOSTS)
)

# CapRover terminates TLS in nginx; trust its forwarded headers.
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = get_env_bool("SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

REDIS_URL = get_env("REDIS_URL", "")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }

# Never the console backend in production (the Mailgun backend arrives with
# tripaulx.mail; until then SMTP is configured through MAIL_* variables).
MAILERS = {
    "default": {
        "BACKEND": get_env(
            "MAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
        ),
        "OPTIONS": {
            "host": get_env("MAIL_HOST", "localhost"),
            "port": int(get_env("MAIL_PORT", "587")),
            "username": get_env("MAIL_USER", ""),
            "password": get_env("MAIL_PASSWORD", ""),
            "use_tls": get_env_bool("MAIL_USE_TLS", default=True),
        },
    },
}

WHITENOISE_MAX_AGE = 31536000
STORAGES = {
    **STORAGES,  # noqa: F405
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
