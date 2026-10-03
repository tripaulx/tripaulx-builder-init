"""Logging configuration with secret redaction on every console line."""

from __future__ import annotations


def logging_config(level: str = "INFO") -> dict:
    """Return a ``LOGGING`` dict whose console handler redacts secrets.

    The ``redact_secrets`` filter masks e-mails, bearer tokens, JWTs, API keys
    and one-time codes before anything reaches the log (see
    :mod:`tripaulx.core.logs.redaction`).
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {module} {process:d} {message}",
                "style": "{",
            },
        },
        "filters": {
            "redact_secrets": {
                "()": "tripaulx.core.logs.redaction.RedactSecretsFilter",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "filters": ["redact_secrets"],
            },
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            "django": {"handlers": ["console"], "level": level, "propagate": False},
        },
    }
