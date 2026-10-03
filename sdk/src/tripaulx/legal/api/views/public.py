"""Public documents (terms of use, privacy policy): anyone, any schema."""

from __future__ import annotations

from django.utils.cache import patch_cache_control, patch_vary_headers
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from ...conf import app_settings
from ...services import PUBLIC, get_document, list_documents, summary
from ..serializers import LegalDocumentDetailSerializer, LegalDocumentListSerializer
from .base import LegalAPIView


class PublicLegalView(LegalAPIView):
    """No authentication at all, and cacheable per language."""

    permission_classes = [AllowAny]
    # A stale or foreign token must never turn a public page into a 401.
    authentication_classes: list = []

    def set_cache_headers(self, response: Response) -> None:
        """Let browsers and CDNs cache successful answers."""
        if response.status_code == 200:
            patch_cache_control(
                response, public=True, max_age=app_settings.LEGAL_PUBLIC_CACHE_SECONDS
            )
        patch_vary_headers(response, ("Accept-Language",))


class PublicLegalDocumentListView(PublicLegalView):
    """List the public documents."""

    @extend_schema(
        operation_id="legal_public_list", responses=LegalDocumentListSerializer
    )
    def get(self, request: Request) -> Response:
        """Return ``{"documents": [...]}`` in editorial order."""
        return Response({"documents": [summary(d) for d in list_documents(PUBLIC)]})


class PublicLegalDocumentDetailView(PublicLegalView):
    """Serve one public document; restricted slugs answer 404."""

    @extend_schema(
        operation_id="legal_public_retrieve", responses=LegalDocumentDetailSerializer
    )
    def get(self, request: Request, slug: str) -> Response:
        """Return the document, 404 for an unknown or restricted slug."""
        return self.document_response(get_document(slug, PUBLIC))
