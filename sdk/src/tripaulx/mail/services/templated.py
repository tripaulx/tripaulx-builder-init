"""Send branded e-mails rendered from overridable Django templates.

Every e-mail has a plain-text and an HTML version, rendered from
``tripaulx/mail/<name>.txt`` and ``tripaulx/mail/<name>.html``. A project
overrides any of them by creating the same path in its ``templates/`` folder.
The brand (``APP_NAME`` and ``EMAIL_LOGO_URL``) comes from ``TRIPAULX``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from tripaulx.core.conf import app_settings as core_settings

from ..conf import app_settings


def brand_context() -> dict[str, str]:
    """Return the brand variables available to every e-mail template."""
    return {
        "app_name": core_settings.APP_NAME,
        "logo_url": app_settings.EMAIL_LOGO_URL,
    }


def render_mail(name: str, context: Mapping[str, Any]) -> tuple[str, str]:
    """Render the text and HTML bodies of the e-mail ``name``."""
    full = {**brand_context(), **context}
    text = render_to_string(f"tripaulx/mail/{name}.txt", full)
    html = render_to_string(f"tripaulx/mail/{name}.html", full)
    return text.strip() + "\n", html


def send_templated_mail(
    name: str, *, subject: str, to: list[str], context: Mapping[str, Any]
) -> int:
    """Render the e-mail ``name`` and send it with the default mailer."""
    text, html = render_mail(name, context)
    message = EmailMultiAlternatives(
        subject=str(subject),
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to,
    )
    message.attach_alternative(html, "text/html")
    return message.send()
