"""Shapes of the legal API responses; the views build plain dicts."""

from __future__ import annotations

from rest_framework import serializers


class LegalDocumentSummarySerializer(serializers.Serializer):
    """One entry of the document list."""

    slug = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    audience = serializers.ChoiceField(choices=("public", "restricted"))


class LegalDocumentListSerializer(serializers.Serializer):
    """``{"documents": [...]}`` in editorial order."""

    documents = LegalDocumentSummarySerializer(many=True)


class LegalDocumentDetailSerializer(serializers.Serializer):
    """One document rendered to sanitized HTML."""

    slug = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    html = serializers.CharField()
