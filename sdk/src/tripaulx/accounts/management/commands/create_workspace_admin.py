r"""Create the administrator of a workspace, asking for every field.

Interactive (the password is typed twice and never echoed)::

    manage.py create_workspace_admin --schema main

Non-interactive (CI, provisioning scripts)::

    printf '%s\n' "$PASSWORD" | manage.py create_workspace_admin --schema main \
        --email ana@example.com --full-name "Ana Souza" --password-stdin

The password rules shown and enforced are the project's
``AUTH_PASSWORD_VALIDATORS``.
"""

from __future__ import annotations

from getpass import getpass
import sys
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.translation import gettext as _

from ...models import Role
from ...services import admins, identity
from ...services.errors import AccountsError

ATTEMPTS = 3


class Command(BaseCommand):
    """Management command entry point."""

    help = "Create a workspace administrator (full name, e-mail, password twice)."

    def add_arguments(self, parser: CommandParser) -> None:
        """Declare the workspace, identity, role and input options."""
        parser.add_argument("--schema", required=True, help="Workspace slug.")
        parser.add_argument("--email", default="")
        parser.add_argument("--full-name", default="")
        parser.add_argument(
            "--role", default=Role.OWNER, choices=[r.value for r in Role]
        )
        parser.add_argument(
            "--no-superuser",
            action="store_true",
            help="Do not give access to the Django admin.",
        )
        parser.add_argument(
            "--if-none",
            action="store_true",
            help="Do nothing when the workspace already has an owner (onboarding).",
        )
        parser.add_argument(
            "--password-stdin",
            action="store_true",
            help="Read the password from the first line of stdin.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Ask for what is missing, validate, create, report."""
        schema, stdin = options["schema"], options["password_stdin"]
        if options["if_none"] and admins.has_owner(schema):
            self.stdout.write(
                _("Workspace %(schema)s already has an owner; skipping.")
                % {"schema": schema}
            )
            return
        if stdin and not (options["email"] and options["full_name"]):
            raise CommandError(_("--password-stdin needs --email and --full-name."))
        email = options["email"] or input(_("E-mail (login): ")).strip()
        full_name = options["full_name"] or input(_("Full name: ")).strip()
        try:
            email, _first, _last = admins.check_identity(schema, email, full_name)
        except AccountsError as exc:
            raise CommandError(exc.message) from exc
        user = self._create(options, email, full_name, stdin)
        self.stdout.write(
            self.style.SUCCESS(
                _("Created %(email)s (%(role)s) in workspace %(schema)s.")
                % {
                    "email": user.email,
                    "role": user.get_role_display(),
                    "schema": schema,
                }
            )
        )

    def _create(self, options: dict, email: str, full_name: str, stdin: bool) -> Any:
        """Ask for the password (twice) until it passes, or fail."""
        if not stdin:
            self.stdout.write(_("Password rules:"))
            for rule in identity.password_rules():
                self.stdout.write(f"  - {rule}")
        for _attempt in range(1 if stdin else ATTEMPTS):
            if stdin:
                password = sys.stdin.readline().rstrip("\n")
                confirmation = password
            else:
                password = getpass(_("Password: "))
                confirmation = getpass(_("Password (again): "))
            try:
                return admins.create_admin(
                    options["schema"],
                    email,
                    full_name,
                    password,
                    confirmation,
                    role=options["role"],
                    superuser=not options["no_superuser"],
                )
            except AccountsError as exc:
                self.stderr.write(self.style.ERROR(exc.message))
        raise CommandError(_("No administrator was created."))
