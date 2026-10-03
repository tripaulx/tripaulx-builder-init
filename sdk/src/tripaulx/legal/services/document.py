"""The ``LegalDocument`` entry and its whitelist rules."""

from __future__ import annotations

from dataclasses import dataclass
import re

from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import Promise

PUBLIC = "public"
RESTRICTED = "restricted"
AUDIENCES = (PUBLIC, RESTRICTED)

_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
# A relative path of plain names: no ``..``, no absolute path, no backslash.
_FILENAME_RE = re.compile(
    r"[A-Za-z0-9_-][A-Za-z0-9._-]*(/[A-Za-z0-9_-][A-Za-z0-9._-]*)*"
)


@dataclass(frozen=True)
class LegalDocument:
    """Metadata of one published document and the file holding it."""

    slug: str
    title: str | Promise
    description: str | Promise
    filename: str
    category: str | Promise
    audience: str = RESTRICTED

    def __post_init__(self) -> None:
        """Refuse slugs, file names and audiences outside the whitelist."""
        if not _SLUG_RE.fullmatch(self.slug):
            raise ImproperlyConfigured(f"Invalid legal document slug: {self.slug!r}")
        if not _FILENAME_RE.fullmatch(self.filename) or ".." in self.filename:
            raise ImproperlyConfigured(
                f"Invalid legal document filename: {self.filename!r}"
            )
        if self.audience not in AUDIENCES:
            raise ImproperlyConfigured(
                f"Invalid legal document audience: {self.audience!r}"
            )

    @property
    def is_public(self) -> bool:
        """Whether anyone may read the document, signed in or not."""
        return self.audience == PUBLIC
