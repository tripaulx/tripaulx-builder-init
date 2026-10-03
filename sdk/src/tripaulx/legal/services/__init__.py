"""Public API of the legal app."""

from .access import can_read_restricted, email_domain_allowed, schema_allowed
from .catalog import (
    AUDIENCES,
    DEFAULT_DOCUMENTS,
    PUBLIC,
    RESTRICTED,
    LegalDocument,
    get_document,
    list_documents,
)
from .markdown import render_markdown, safe_href
from .placeholders import context, fill, unfilled
from .render import detail, render_document, summary
from .sources import DocumentUnavailable, package_content_root, read_source, resolve

__all__ = [
    "AUDIENCES",
    "DEFAULT_DOCUMENTS",
    "PUBLIC",
    "RESTRICTED",
    "DocumentUnavailable",
    "LegalDocument",
    "can_read_restricted",
    "context",
    "detail",
    "email_domain_allowed",
    "fill",
    "get_document",
    "list_documents",
    "package_content_root",
    "read_source",
    "render_document",
    "render_markdown",
    "resolve",
    "safe_href",
    "schema_allowed",
    "summary",
    "unfilled",
]
