"""``manage.py ai_purge_content``: purge old AI event content (metrics stay)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from tripaulx.ai.services import retention


class Command(BaseCommand):
    """Clear content of events older than each workspace's retention days."""

    help = (
        "Clear the prompt, input and output of AI events older than the "
        "retention days of each workspace. Metrics are kept."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        """Declare ``--schema`` (repeatable) and ``--days``."""
        parser.add_argument(
            "--schema",
            action="append",
            dest="schemas",
            help="Only this workspace schema (repeatable). Default: all.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Override the retention days of every workspace.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Run the purge and print the count per schema."""
        counts = retention.purge_all_workspaces(
            days=options["days"], schemas=options["schemas"]
        )
        for schema, count in counts.items():
            self.stdout.write(f"{schema}: {count}")
        self.stdout.write(self.style.SUCCESS(f"{sum(counts.values())} events purged."))
