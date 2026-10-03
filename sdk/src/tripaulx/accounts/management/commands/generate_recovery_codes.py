"""Generate 2FA recovery codes for a user of a workspace.

The codes are printed once in plain text (only hashes are stored), and a new
list invalidates the previous one. Usage::

    manage.py generate_recovery_codes --schema acme --user jane@example.com
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django_tenants.utils import schema_context

from ...conf import app_settings
from ...services import recovery_codes


class Command(BaseCommand):
    """Management command entry point."""

    help = "Generate single-use 2FA recovery codes for a user."

    def add_arguments(self, parser: CommandParser) -> None:
        """Declare --schema, --user, --quantity and --label."""
        parser.add_argument("--schema", required=True, help="Workspace schema.")
        parser.add_argument("--user", required=True, help="E-mail of the user.")
        parser.add_argument(
            "--quantity", type=int, default=app_settings.RECOVERY_CODES_QUANTITY
        )
        parser.add_argument("--label", default="", help="Free label for the list.")

    def handle(self, *args: Any, **options: Any) -> None:
        """Generate and print the codes inside the workspace schema."""
        if options["quantity"] < 1:
            raise CommandError("--quantity must be at least 1.")
        with schema_context(options["schema"]):
            user = get_user_model().objects.filter(email__iexact=options["user"])
            user = user.first()
            if user is None:
                raise CommandError(
                    f"No user '{options['user']}' in schema '{options['schema']}'."
                )
            previous = recovery_codes.remaining(user)
            codes = recovery_codes.generate_codes(
                user, options["quantity"], options["label"]
            )
        self._print(codes, previous)

    def _print(self, codes: list[str], previous: int) -> None:
        """Print the list and the warnings."""
        self.stdout.write(self.style.SUCCESS(f"{len(codes)} recovery codes:"))
        if previous:
            self.stdout.write(
                self.style.WARNING(f"{previous} codes of the previous list revoked.")
            )
        for index, code in enumerate(codes, start=1):
            self.stdout.write(f"  {index:>2}. {code}")
        self.stdout.write(
            self.style.NOTICE(
                "Store this list now; it is never shown again. Each code "
                "completes one login in place of the second factor."
            )
        )
