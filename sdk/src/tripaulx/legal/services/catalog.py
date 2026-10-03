"""Closed catalog of the published legal documents.

Only slugs listed here (the SDK defaults plus ``LEGAL_EXTRA_DOCUMENTS``, minus
``LEGAL_EXCLUDED_DOCUMENTS``) are ever resolved: a request never chooses a
file path.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..conf import app_settings
from .defaults import DEFAULT_DOCUMENTS
from .document import AUDIENCES, PUBLIC, RESTRICTED, LegalDocument

__all__ = [
    "AUDIENCES",
    "DEFAULT_DOCUMENTS",
    "PUBLIC",
    "RESTRICTED",
    "LegalDocument",
    "get_document",
    "list_documents",
]


def _extra(entry: LegalDocument | Mapping[str, Any]) -> LegalDocument:
    """Build a document from a ``LEGAL_EXTRA_DOCUMENTS`` entry."""
    if isinstance(entry, LegalDocument):
        return entry
    return LegalDocument(**entry)


def list_documents(audience: str | None = None) -> tuple[LegalDocument, ...]:
    """Return the catalog in editorial order, optionally of one audience."""
    by_slug = {document.slug: document for document in DEFAULT_DOCUMENTS}
    for entry in app_settings.LEGAL_EXTRA_DOCUMENTS:
        document = _extra(entry)
        by_slug[document.slug] = document
    excluded = set(app_settings.LEGAL_EXCLUDED_DOCUMENTS)
    return tuple(
        document
        for document in by_slug.values()
        if document.slug not in excluded
        and (audience is None or document.audience == audience)
    )


def get_document(slug: str, audience: str | None = None) -> LegalDocument | None:
    """Resolve only explicitly published slugs (``None`` for anything else)."""
    for document in list_documents(audience):
        if document.slug == slug:
            return document
    return None
