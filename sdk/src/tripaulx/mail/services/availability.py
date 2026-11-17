"""Whether e-mail actually reaches people (or a local inbox) right now.

Clients use it to hide flows that depend on e-mail (codes, invitations)
while no provider is configured.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings

from ..backends.mailgun import DEFAULT_FALLBACK
from ..models import MailgunConfig

MAILGUN = "tripaulx.mail.backends.MailgunEmailBackend"
SMTP = "django.core.mail.backends.smtp.EmailBackend"

#: Backends that keep messages locally (console, tests, files): every flow
#: that sends e-mail can be exercised, so e-mail counts as available.
LOCAL_BACKENDS = frozenset(
    {
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.locmem.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend",
    }
)


def default_mailer() -> tuple[str, dict[str, Any]]:
    """Return the default mailer's backend path and options.

    Reads ``MAILERS`` (Django 6.1+) and falls back to ``EMAIL_BACKEND``.
    """
    mailers = getattr(settings, "MAILERS", None) or {}
    if "default" in mailers:
        mailer = mailers["default"]
        return mailer["BACKEND"], dict(mailer.get("OPTIONS") or {})
    host = getattr(settings, "EMAIL_HOST", "")
    return getattr(settings, "EMAIL_BACKEND", ""), {"host": host}


def _smtp_ready(options: dict[str, Any]) -> bool:
    """Whether an SMTP host is set."""
    return bool(options.get("host"))


def email_available() -> bool:
    """Tell whether sent e-mail is delivered (Mailgun ready, SMTP host, local)."""
    backend, options = default_mailer()
    if backend in LOCAL_BACKENDS:
        return True
    if backend == SMTP:
        return _smtp_ready(options)
    if backend == MAILGUN:
        if MailgunConfig.load().is_ready:
            return True
        fallback = options.get("fallback_backend") or DEFAULT_FALLBACK
        if fallback in LOCAL_BACKENDS:
            return True
        return fallback == SMTP and _smtp_ready(options.get("fallback_options") or {})
    return False
