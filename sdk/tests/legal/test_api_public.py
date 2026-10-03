"""Public documents: anyone, on workspaces and on the apex domain."""

import pytest
from rest_framework.test import APIClient

from tripaulx.core.testing import TenantAPITestCase
from tripaulx.tenants.services import bootstrap

PUBLIC = "/api/legal/public/"


class PublicOnWorkspaceTests(TenantAPITestCase):
    def test_lists_only_public_documents(self):
        response = self.anon_api_client().get(PUBLIC)

        assert response.status_code == 200
        slugs = [item["slug"] for item in response.data["documents"]]
        assert slugs == ["terms-of-use", "privacy-policy"]

    def test_detail_is_cacheable_per_language(self):
        response = self.anon_api_client().get(f"{PUBLIC}privacy-policy/")

        assert response.status_code == 200
        assert "<h1>Privacy policy</h1>" in response.data["html"]
        assert "public" in response["Cache-Control"]
        assert "max-age=3600" in response["Cache-Control"]
        assert "Accept-Language" in response["Vary"]
        assert response["X-Content-Type-Options"] == "nosniff"

    def test_restricted_slug_is_404_here(self):
        response = self.anon_api_client().get(f"{PUBLIC}risk-matrix/")
        assert response.status_code == 404
        assert "max-age" not in response.get("Cache-Control", "")

    def test_a_bad_token_does_not_block_public_pages(self):
        client = self.anon_api_client()
        client.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")
        assert client.get(f"{PUBLIC}terms-of-use/").status_code == 200


@pytest.mark.django_db
def test_public_schema_serves_terms(public_schema):
    public, _created = bootstrap.ensure_public()
    bootstrap.ensure_domain("sdk.test", public, primary=False)
    client = APIClient(HTTP_HOST="sdk.test")

    response = client.get(f"{PUBLIC}terms-of-use/", HTTP_ACCEPT_LANGUAGE="pt-br")

    assert response.status_code == 200
    assert response.data["title"] == "Termos de uso"
    assert client.get(f"{PUBLIC}risk-matrix/").status_code == 404
