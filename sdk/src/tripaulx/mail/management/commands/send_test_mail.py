"""Send one of the e-mail templates with sample data, to check delivery."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import translation

from ...services import (
    email_available,
    sample_context,
    sample_names,
    send_templated_mail,
)


class Command(BaseCommand):
    """``manage.py send_test_mail --to you@example.com [--template ...]``."""

    help = "Send a sample transactional e-mail (checks the provider and templates)."

    def add_arguments(self, parser: CommandParser) -> None:
        """Declare the options."""
        parser.add_argument("--to", required=True, help="Recipient address.")
        parser.add_argument(
            "--template",
            default="password_reset",
            help="E-mail to send (see tripaulx.mail.services.samples).",
        )
        parser.add_argument(
            "--lang", default="", help="Language code (default: LANGUAGE_CODE)."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Render and send the e-mail."""
        name = options["template"]
        if name not in sample_names():
            known = ", ".join(sample_names())
            raise CommandError(f"Unknown template {name!r}. Choose from: {known}.")
        if not email_available():
            self.stderr.write(
                "E-mail is not configured: set up Mailgun in the public admin "
                "or the SMTP host. The message goes to the fallback backend."
            )
        with translation.override(options["lang"] or settings.LANGUAGE_CODE):
            sent = send_templated_mail(
                name,
                subject=f"[test] {name}",
                to=[options["to"]],
                context=sample_context(name),
            )
        self.stdout.write(f"{name}: {sent} message(s) handed to the mailer.")
