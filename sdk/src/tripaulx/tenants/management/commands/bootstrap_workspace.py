"""Create or update the public schema and an initial workspace (idempotent).

Usage::

    manage.py bootstrap_workspace
    manage.py bootstrap_workspace --schema acme --name "Acme"
    manage.py bootstrap_workspace --schema acme --domain acme.example.com

Defaults come from ``settings.TRIPAULX`` (``BASE_DOMAIN``, ``PUBLIC_DOMAINS``,
``BOOTSTRAP_WORKSPACE``, ``BOOTSTRAP_WORKSPACE_NAME``).
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from ...conf import app_settings
from ...services import bootstrap
from ...services.domains import public_domains, workspace_domain
from ...validators.slug import validate_workspace_slug


class Command(BaseCommand):
    """Management command entry point."""

    help = "Create or update the public schema and an initial workspace."

    def add_arguments(self, parser: CommandParser) -> None:
        """Declare --schema, --name, --domain and --public-domain."""
        parser.add_argument("--schema", default=app_settings.BOOTSTRAP_WORKSPACE)
        parser.add_argument("--name", default=app_settings.BOOTSTRAP_WORKSPACE_NAME)
        parser.add_argument("--domain", action="append", default=None)
        parser.add_argument("--public-domain", action="append", default=None)

    def handle(self, *args: Any, **options: Any) -> None:
        """Ensure the public schema, then the workspace when one is given."""
        public, created = bootstrap.ensure_public()
        self._report("public schema", created)
        domains = options["public_domain"] or public_domains()
        self._report_domains(
            bootstrap.ensure_domains(domains, public, first_is_primary=False)
        )

        schema = options["schema"]
        if not schema:
            return
        validate_workspace_slug(schema)
        workspace, created = bootstrap.ensure_workspace(
            schema, options["name"] or schema.replace("_", " ").title()
        )
        self._report(f"workspace '{schema}'", created)
        domains = options["domain"] or [workspace_domain(schema)]
        self._report_domains(
            bootstrap.ensure_domains(domains, workspace, first_is_primary=True)
        )

    def _report(self, what: str, created: bool) -> None:
        """Print whether ``what`` was created or already existed."""
        status = "created" if created else "already existed"
        self.stdout.write(f"[bootstrap_workspace] {what}: {status}")

    def _report_domains(self, results: list[bootstrap.DomainResult]) -> None:
        """Print one line per domain, warning about conflicts."""
        for result in results:
            if result.conflict:
                self.stdout.write(
                    self.style.WARNING(
                        f"[bootstrap_workspace] domain '{result.domain}' points "
                        "to another workspace; left unchanged"
                    )
                )
                continue
            self._report(f"domain '{result.domain}'", result.created)
