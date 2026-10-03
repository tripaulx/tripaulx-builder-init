"""E-mail backend that sends through the Mailgun HTTP API.

The configuration (key, domain, region, sender) is read from the
:class:`~tripaulx.mail.models.MailgunConfig` singleton in the public schema,
so it can be changed in the admin without a deploy. While it is not ready
(disabled, no key or no domain), messages go to a fallback backend instead,
so nothing breaks before Mailgun is configured.

Configure it with Django 6.1 ``MAILERS``; every key in ``OPTIONS`` is a
keyword argument of :class:`MailgunEmailBackend`::

    MAILERS = {
        "default": {
            "BACKEND": "tripaulx.mail.backends.MailgunEmailBackend",
            "OPTIONS": {
                "fallback_backend": "django.core.mail.backends.smtp.EmailBackend",
                "fallback_options": {"host": "smtp.example.com", "port": 587},
                "timeout": 10,
            },
        },
    }
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from email.utils import formataddr, parseaddr
import logging
from typing import Any
import urllib.error
import urllib.request

from django.core.mail import EmailMessage
from django.core.mail.backends.base import BaseEmailBackend
from django.utils.module_loading import import_string

from ..models import MailgunConfig
from .multipart import encode_multipart

logger = logging.getLogger("tripaulx.mail")

DEFAULT_FALLBACK = "django.core.mail.backends.console.EmailBackend"


class MailgunEmailBackend(BaseEmailBackend):
    """Send messages with Mailgun, or with the fallback backend until ready."""

    def __init__(
        self,
        fail_silently: bool = False,
        *,
        fallback_backend: str = DEFAULT_FALLBACK,
        fallback_options: dict[str, Any] | None = None,
        timeout: float = 10,
        **kwargs: Any,
    ) -> None:
        """Store the options; unknown ones are rejected by Django."""
        super().__init__(**kwargs)
        self.fail_silently = fail_silently
        self.fallback_backend = fallback_backend or DEFAULT_FALLBACK
        self.fallback_options = dict(fallback_options or {})
        self.timeout = timeout

    def fallback(self) -> BaseEmailBackend:
        """Instantiate the fallback backend with its own options."""
        return import_string(self.fallback_backend)(**self.fallback_options)

    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        """Send every message; return how many Mailgun accepted."""
        if not email_messages:
            return 0
        config = MailgunConfig.load()
        if not config.is_ready:
            return self.fallback().send_messages(email_messages) or 0
        sent = 0
        for message in email_messages:
            try:
                sent += int(self._send_one(config, message))
            except (urllib.error.URLError, OSError):
                logger.exception("Mailgun did not accept an e-mail")
                if not self.fail_silently:
                    raise
        return sent

    @staticmethod
    def from_header(config: MailgunConfig, message: EmailMessage) -> str:
        """Build ``From``, adding the configured display name when missing."""
        raw = message.from_email or config.default_from_email
        name, address = parseaddr(raw)
        if not name and config.default_from_name and address:
            return formataddr((config.default_from_name, address))
        return raw

    @staticmethod
    def fields(from_email: str, message: EmailMessage) -> list[tuple[str, str]]:
        """Map a message to Mailgun form fields (recipients, subject, bodies)."""
        fields = [("from", from_email)]
        fields += [("to", address) for address in message.to]
        fields += [("cc", address) for address in message.cc]
        fields += [("bcc", address) for address in message.bcc]
        fields += [("subject", str(message.subject or "")), ("text", message.body)]
        for content, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype == "text/html":
                fields.append(("html", str(content)))
                break
        return fields

    def _send_one(self, config: MailgunConfig, message: EmailMessage) -> bool:
        """POST one message to ``<base_url>/<domain>/messages``."""
        body, content_type = encode_multipart(
            self.fields(self.from_header(config, message), message)
        )
        credentials = base64.b64encode(f"api:{config.api_key}".encode()).decode()
        request = urllib.request.Request(
            f"{config.base_url}/{config.domain}/messages", data=body, method="POST"
        )
        request.add_header("Authorization", f"Basic {credentials}")
        request.add_header("Content-Type", content_type)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
        return 200 <= int(status) < 300
