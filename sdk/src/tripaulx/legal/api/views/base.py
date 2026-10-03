"""Shared behaviour of the legal endpoints."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ...services import DocumentUnavailable, LegalDocument, detail


class LegalAPIView(APIView):
    """Base view: the detail answer with its 404 and 503 cases, and headers."""

    def document_response(self, document: LegalDocument | None) -> Response:
        """Answer the detail of ``document`` (404 if None, 503 if unreadable)."""
        if document is None:
            return Response(
                {"detail": _("Document not found.")}, status=status.HTTP_404_NOT_FOUND
            )
        try:
            body = detail(document)
        except DocumentUnavailable:
            return Response(
                {"detail": _("Document temporarily unavailable.")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(body)

    def set_cache_headers(self, response: Response) -> None:
        """Set ``Cache-Control`` (subclasses decide)."""

    def finalize_response(
        self, request: Request, response: Response, *args: Any, **kwargs: Any
    ) -> Response:
        """Add ``nosniff`` and the cache policy to every answer."""
        response = super().finalize_response(request, response, *args, **kwargs)
        response["X-Content-Type-Options"] = "nosniff"
        self.set_cache_headers(response)
        return response
