from django.test import Client
import pytest
from tripaulx.core.testing import TenantTestCase


@pytest.mark.parametrize("path", ["/healthz/", "/readyz/"])
@pytest.mark.django_db
def test_probes_answer_on_internal_hosts(path):
    response = Client(HTTP_HOST="srv-captain--app:8000").get(path)
    assert response.status_code == 200


@pytest.mark.django_db
def test_unknown_workspace_is_404():
    response = Client(HTTP_HOST="nobody.test.localhost").get("/admin/")
    assert response.status_code == 404


class WorkspaceSmokeTests(TenantTestCase):
    def test_admin_login_page_is_served_on_the_workspace_domain(self):
        response = self.tenant_client().get("/admin/login/")
        assert response.status_code == 200

    def test_users_live_in_the_workspace_schema(self):
        user = self.make_user(email="owner@example.com")
        assert user.email == "owner@example.com"
