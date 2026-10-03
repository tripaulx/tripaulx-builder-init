"""Generate a master key for file encryption (``FILE_ENCRYPTION_KEY``).

Usage::

    manage.py generate_file_key
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from ...crypto import generate_master_key


class Command(BaseCommand):
    """Management command entry point."""

    help = "Generate a new master key for the encryption of stored files."

    def handle(self, *args: Any, **options: Any) -> None:
        """Print a fresh key and the warning that comes with it."""
        self.stdout.write(
            self.style.SUCCESS(f"FILE_ENCRYPTION_KEY={generate_master_key()}")
        )
        self.stdout.write(
            self.style.WARNING(
                "Keep this key somewhere safe and OUTSIDE the server (a password\n"
                "manager). Losing it means losing EVERY encrypted file: the\n"
                "objects in the bucket become unreadable forever.\n"
                "Changing it later requires re-encrypting the stored files while\n"
                "the old key is still available."
            )
        )
