from pathlib import Path

from django.conf import settings
from django.db import connection
import pytest
from rest_framework.test import APIClient
from tripaulx.accounts.models import Role
from tripaulx.core.testing import TenantAPITestCase
from tripaulx.legal.services import get_document, resolve
from tripaulx.tenants.services import bootstrap


def test_project_legal_folder_overrides_the_sdk():
    folder = Path(settings.BASE_DIR) / "legal"
    assert str(folder) in settings.TRIPAULX["LEGAL_CONTENT_DIRS"]
    assert (folder / "README.md").is_file()
    assert resolve(get_document("terms-of-use"), "en") is not None


class LegalApiTests(TenantAPITestCase):
    def test_terms_are_public_on_workspaces(self):
        response = self.anon_api_client().get("/api/legal/public/terms-of-use/")
        assert response.status_code == 200
        assert response.data["html"].startswith("<h1>")

    def test_governance_documents_need_an_admin(self):
        member = self.make_user(email_verified=True)
        assert self.api_client(member).get("/api/v1/legal/").status_code == 403
        admin = self.make_user(
            email="admin@example.com", email_verified=True, role=Role.ADMIN
        )
        response = self.api_client(admin).get("/api/v1/legal/risk-matrix/")
        assert response.status_code == 200
        assert response["Cache-Control"] == "private, no-store"


@pytest.mark.django_db
def test_privacy_policy_on_the_public_domain():
    connection.set_schema_to_public()
    public, _created = bootstrap.ensure_public()
    bootstrap.ensure_domain("test.localhost", public, primary=False)
    client = APIClient(HTTP_HOST="test.localhost")
    response = client.get("/api/legal/public/privacy-policy/")
    assert response.status_code == 200
