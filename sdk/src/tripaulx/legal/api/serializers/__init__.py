"""Response serializers of the legal API (used for the OpenAPI schema)."""

from .documents import (
    LegalDocumentDetailSerializer,
    LegalDocumentListSerializer,
    LegalDocumentSummarySerializer,
)

__all__ = [
    "LegalDocumentDetailSerializer",
    "LegalDocumentListSerializer",
    "LegalDocumentSummarySerializer",
]
