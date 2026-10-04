import re

from django.core import mail
from django.db import connection
import pytest
from rest_framework.test import APIClient
from tripaulx.core.testing import TenantAPITestCase
from tripaulx.tenants.services import bootstrap

PASSWORD = "correct-horse-battery-42"


class LoginSmokeTests(TenantAPITestCase):
    def test_login_with_email_code_reaches_me(self):
        self.make_user(email="jane@example.com", password=PASSWORD, email_verified=True)
        client = self.anon_api_client()
        body = {"email": "jane@example.com", "password": PASSWORD}
        start = client.post("/api/auth/login/", body, format="json")
        assert start.data["mfa_required"] is True
        code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)
        done = client.post(
            "/api/auth/login/verify/",
            {"ticket": start.data["ticket"], "code": code},
            format="json",
        )
        assert done.status_code == 200
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {done.data['access']}")
        assert client.get("/api/auth/me/").data["email"] == "jane@example.com"

    def test_workspace_routes_need_an_admin(self):
        client = self.api_client(self.make_user())
        assert client.get("/api/workspace/members/").status_code == 403

    def test_signup_is_not_served_on_workspaces(self):
        resp = self.anon_api_client().post("/api/auth/signup/", {}, format="json")
        assert resp.status_code == 404


@pytest.mark.django_db
def test_signup_on_the_public_domain():
    connection.set_schema_to_public()
    public, _created = bootstrap.ensure_public()
    bootstrap.ensure_domain("test.localhost", public, primary=False)
    body = {
        "email": "owner@example.com",
        "full_name": "Ana Souza",
        "password": PASSWORD,
        "password_confirm": PASSWORD,
        "workspace_name": "Acme",
    }
    client = APIClient(HTTP_HOST="test.localhost")
    resp = client.post("/api/auth/signup/", body, format="json")
    assert resp.status_code == 201, resp.content
    assert resp.data["workspace_domain"] == "acme.test.localhost"
