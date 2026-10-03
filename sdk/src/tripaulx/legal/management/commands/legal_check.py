"""Report unfilled placeholders and unreadable documents, per language.

Run it before going live and in CI: it fails while any document still shows a
``{{ key }}`` without a value in ``TRIPAULX["LEGAL_CONTEXT"]``.

Usage::

    manage.py legal_check
    manage.py legal_check --language pt-br --language en
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import translation

from ...services import DocumentUnavailable, list_documents, read_source, resolve
from ...services.placeholders import unfilled


class Command(BaseCommand):
    """Check every catalog document in each language."""

    help = "List unfilled {{ placeholders }} and unreadable legal documents."

    def add_arguments(self, parser: CommandParser) -> None:
        """Declare --language (repeatable)."""
        parser.add_argument(
            "--language",
            action="append",
            dest="languages",
            help="Language to check (default: LANGUAGE_CODE and en).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Check the documents and fail when anything is missing."""
        languages = options["languages"] or [settings.LANGUAGE_CODE, "en"]
        problems = 0
        for language in dict.fromkeys(languages):
            with translation.override(language):
                problems += self._check_language(language)
        if problems:
            raise CommandError(f"{problems} legal document(s) need attention.")
        self.stdout.write(self.style.SUCCESS("Every legal document is complete."))

    def _check_language(self, language: str) -> int:
        """Report each document of ``language``; return how many have issues."""
        self.stdout.write(f"[{language}]")
        problems = 0
        for document in list_documents():
            try:
                missing = unfilled(read_source(document, language))
            except DocumentUnavailable:
                self.stdout.write(self.style.ERROR(f"  {document.slug}: unreadable"))
                problems += 1
                continue
            path = resolve(document, language)
            if missing:
                problems += 1
                keys = ", ".join(missing)
                self.stdout.write(
                    self.style.WARNING(f"  {document.slug}: missing {keys} ({path})")
                )
            else:
                self.stdout.write(f"  {document.slug}: ok ({path})")
        return problems
