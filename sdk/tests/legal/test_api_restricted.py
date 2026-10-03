"""Restricted legal area: who gets in, and what the answers look like."""

from unittest import mock

from django.test import override_settings

from tripaulx.accounts.models import Role
from tripaulx.core.testing import TenantAPITestCase

BASE = "/api/v1/legal/"


class LegalAPITestCase(TenantAPITestCase):
    def setUp(self):
        legal = {"LEGAL_ALLOWED_EMAIL_DOMAINS": ("example.com",)}
        settings = override_settings(TRIPAULX=legal)
        settings.enable()
        self.addCleanup(settings.disable)
        self.client_auth = self.api_client(self.verified("tech@example.com"))

    def verified(self, email, **extra):
        return self.make_user(email=email, email_verified=True, **extra)


class RestrictedAccessTests(LegalAPITestCase):
    def test_without_jwt_is_401(self):
        assert self.anon_api_client().get(BASE).status_code == 401

    def test_allowed_domain_lists_documents(self):
        response = self.client_auth.get(BASE)

        assert response.status_code == 200
        slugs = {item["slug"] for item in response.data["documents"]}
        assert {"risk-matrix", "governance-backlog", "privacy-policy"} <= slugs

    def test_other_domain_is_403(self):
        other = self.verified("member@other.test")
        assert self.api_client(other).get(BASE).status_code == 403

    def test_look_alike_domain_is_refused(self):
        other = self.verified("x@example.com.attacker.test")
        assert self.api_client(other).get(BASE).status_code == 403

    def test_unverified_email_is_refused(self):
        other = self.make_user(email="new@example.com")
        assert self.api_client(other).get(BASE).status_code == 403

    def test_workspace_admin_of_any_domain_gets_in(self):
        admin = self.verified("boss@other.test", role=Role.ADMIN)
        assert self.api_client(admin).get(BASE).status_code == 200

    def test_schema_outside_legal_schemas_is_refused(self):
        legal = {
            "LEGAL_ALLOWED_EMAIL_DOMAINS": ("example.com",),
            "LEGAL_SCHEMAS": ("another",),
        }
        with override_settings(TRIPAULX=legal):
            assert self.client_auth.get(BASE).status_code == 403
        legal["LEGAL_SCHEMAS"] = (self.tenant.schema_name,)
        with override_settings(TRIPAULX=legal):
            assert self.client_auth.get(BASE).status_code == 200


class RestrictedDetailTests(LegalAPITestCase):
    def test_detail_is_sanitized_html_never_cached(self):
        response = self.client_auth.get(f"{BASE}risk-matrix/")

        assert response.status_code == 200
        assert set(response.data) == {
            "slug",
            "title",
            "description",
            "category",
            "html",
        }
        assert "<h1>" in response.data["html"]
        assert response["Cache-Control"] == "private, no-store"
        assert response["X-Content-Type-Options"] == "nosniff"

    def test_unknown_slug_is_404(self):
        assert self.client_auth.get(f"{BASE}does-not-exist/").status_code == 404

    def test_read_error_is_503(self):
        with mock.patch(
            "tripaulx.legal.services.sources.Path.read_text",
            side_effect=OSError("disk"),
        ):
            response = self.client_auth.get(f"{BASE}risk-matrix/")
        assert response.status_code == 503
        assert response["Cache-Control"] == "private, no-store"

    def test_answer_follows_the_request_language(self):
        response = self.client_auth.get(
            f"{BASE}risk-matrix/", HTTP_ACCEPT_LANGUAGE="pt-br"
        )
        assert response.data["title"] == "Matriz de riscos de segurança e privacidade"
        assert "<h1>Matriz de riscos" in response.data["html"]
