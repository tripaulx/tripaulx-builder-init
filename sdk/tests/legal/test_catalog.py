"""Closed catalog: whitelisted slugs, safe file names, project entries."""

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
import pytest

from tripaulx.legal.services import (
    PUBLIC,
    RESTRICTED,
    LegalDocument,
    get_document,
    list_documents,
)

EXTRA = {
    "slug": "cookie-policy",
    "title": "Cookie policy",
    "description": "Cookies we use.",
    "filename": "cookie-policy.md",
    "category": "Policies",
    "audience": PUBLIC,
}


class CatalogTests(SimpleTestCase):
    def test_defaults_split_by_audience(self):
        public = {d.slug for d in list_documents(PUBLIC)}
        restricted = {d.slug for d in list_documents(RESTRICTED)}
        assert public == {"terms-of-use", "privacy-policy"}
        assert {"risk-matrix", "incident-response-plan", "data-inventory"} <= restricted
        assert len(restricted) == 6

    def test_only_whitelisted_slugs_resolve(self):
        assert get_document("risk-matrix") is not None
        assert get_document("../settings") is None
        assert get_document("unknown") is None
        assert get_document("risk-matrix", PUBLIC) is None

    def test_invalid_entries_are_refused(self):
        bad = [
            {"slug": "Bad Slug"},
            {"filename": "../secrets.md"},
            {"filename": "/etc/passwd"},
            {"filename": "a/../../b.md"},
            {"audience": "everyone"},
        ]
        for override in bad:
            with pytest.raises(ImproperlyConfigured):
                LegalDocument(**{**EXTRA, **override})

    def test_project_registers_extra_documents(self):
        with override_settings(TRIPAULX={"LEGAL_EXTRA_DOCUMENTS": [EXTRA]}):
            document = get_document("cookie-policy", PUBLIC)
            assert document is not None and document.is_public
            assert list_documents()[-1].slug == "cookie-policy"

    def test_extra_entry_replaces_a_default_and_exclusion_hides(self):
        replaced = {**EXTRA, "slug": "risk-matrix", "title": "Risks"}
        settings = {
            "LEGAL_EXTRA_DOCUMENTS": [replaced],
            "LEGAL_EXCLUDED_DOCUMENTS": ["governance-backlog"],
        }
        with override_settings(TRIPAULX=settings):
            assert get_document("risk-matrix").title == "Risks"
            assert get_document("governance-backlog") is None
