"""Versioned legal and governance documents, rendered as sanitized HTML.

The package ships generic templates (English and pt-BR) with ``{{ key }}``
placeholders; projects fill them through ``TRIPAULX["LEGAL_CONTEXT"]`` and
override them with their own files (``TRIPAULX["LEGAL_CONTENT_DIRS"]``).
The public API lives in :mod:`tripaulx.legal.services`.
"""
