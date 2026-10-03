"""Production settings (CapRover). Fails fast on unsafe configuration."""

from tripaulx.core.crypto import validate_field_key
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

# Encrypted fields (Mailgun key, TOTP secrets) need a real key in production.
validate_field_key(TRIPAULX["FIELD_ENCRYPTION_KEY"])

# Never the console backend in production. Mailgun is configured in the public
# admin; until it is ready, e-mail goes through SMTP (MAIL_* variables).
_SMTP = "django.core.mail.backends.smtp.EmailBackend"
_MAILGUN = "tripaulx.mail.backends.MailgunEmailBackend"
_SMTP_OPTIONS = {
    "host": get_env("MAIL_HOST", "localhost"),
    "port": int(get_env("MAIL_PORT", "587")),
    "username": get_env("MAIL_USER", ""),
    "password": get_env("MAIL_PASSWORD", ""),
    "use_tls": get_env_bool("MAIL_USE_TLS", default=True),
}
_MAIL_BACKEND = get_env("MAIL_BACKEND", _MAILGUN)
if _MAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
    _MAIL_BACKEND = _MAILGUN
MAILERS = {
    "default": {
        "BACKEND": _MAIL_BACKEND,
        "OPTIONS": (
            {"fallback_backend": _SMTP, "fallback_options": _SMTP_OPTIONS}
            if _MAIL_BACKEND == _MAILGUN
            else _SMTP_OPTIONS
        ),
    },
}

WHITENOISE_MAX_AGE = 31536000
STORAGES = {
    **STORAGES,  # noqa: F405
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
