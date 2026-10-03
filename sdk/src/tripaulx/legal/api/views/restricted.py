"""Restricted legal area: every document, for authorized workspace users."""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from ...services import get_document, list_documents, summary
from ..permissions import LegalAccessPermission
from .base import LegalAPIView


class RestrictedLegalView(LegalAPIView):
    """Never cached: the content is internal."""

    permission_classes = [IsAuthenticated, LegalAccessPermission]

    def set_cache_headers(self, response: Response) -> None:
        """Forbid any cache to keep a copy."""
        response["Cache-Control"] = "private, no-store"


class LegalDocumentListView(RestrictedLegalView):
    """List the published documents, public and restricted."""

    def get(self, request: Request) -> Response:
        """Return ``{"documents": [...]}`` in editorial order."""
        return Response({"documents": [summary(d) for d in list_documents()]})


class LegalDocumentDetailView(RestrictedLegalView):
    """Serve one document as sanitized HTML; never an arbitrary path."""

    def get(self, request: Request, slug: str) -> Response:
        """Return the document, 404 for an unknown slug."""
        return self.document_response(get_document(slug))
