"""``manage.py ai_sync_catalog <file>``: load or update the model catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django_tenants.utils import get_public_schema_name, schema_context

from tripaulx.ai.catalog.services.sync import CatalogFileError, read_entries, sync


class Command(BaseCommand):
    """Create or update catalog rows from a JSON or TOML file."""

    help = "Load or update the AI model catalog from a JSON or TOML file."

    def add_arguments(self, parser: CommandParser) -> None:
        """Declare the file path and the ``--prices-only`` flag."""
        parser.add_argument("path", type=Path)
        parser.add_argument(
            "--prices-only",
            action="store_true",
            help="Only update prices of models already in the catalog.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Run the sync in the public schema and print a summary."""
        try:
            entries = read_entries(options["path"])
            with schema_context(get_public_schema_name()):
                result = sync(entries, prices_only=options["prices_only"])
        except CatalogFileError as exc:
            raise CommandError(str(exc)) from exc
        for name in result.created:
            self.stdout.write(f"created {name}")
        for name in result.updated:
            self.stdout.write(f"updated {name}")
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(result.created)} created, {len(result.updated)} updated."
            )
        )
