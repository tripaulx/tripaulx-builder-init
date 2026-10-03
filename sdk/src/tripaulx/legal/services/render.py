"""From a catalog entry to the HTML served by the API."""

from __future__ import annotations

from typing import Any

from .catalog import LegalDocument
from .markdown import render_markdown
from .placeholders import fill
from .sources import read_source


def render_document(document: LegalDocument, language: str | None = None) -> str:
    """Read, fill the placeholders of and render ``document`` as safe HTML.

    Raises :class:`~tripaulx.legal.services.sources.DocumentUnavailable`
    when its file cannot be read.
    """
    return render_markdown(fill(read_source(document, language)))


def summary(document: LegalDocument) -> dict[str, Any]:
    """Return the list entry of ``document`` (translated metadata)."""
    return {
        "slug": document.slug,
        "title": str(document.title),
        "description": str(document.description),
        "category": str(document.category),
        "audience": document.audience,
    }


def detail(document: LegalDocument, language: str | None = None) -> dict[str, Any]:
    """Return the detail payload of ``document``, HTML included."""
    return {
        "slug": document.slug,
        "title": str(document.title),
        "description": str(document.description),
        "category": str(document.category),
        "html": render_document(document, language),
    }
