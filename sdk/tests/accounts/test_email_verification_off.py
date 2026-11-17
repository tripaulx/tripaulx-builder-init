"""With ``EMAIL_VERIFICATION_REQUIRED`` off, new accounts start logged in."""

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django_tenants.utils import schema_context
import pytest
from rest_framework.test import APIClient

from tripaulx.tenants.services import bootstrap

from .helpers import ME, AccountsTestCase

OFF = {
    "APP_NAME": "Acme",
    "BASE_DOMAIN": "sdk.test",
    "EMAIL_VERIFICATION_REQUIRED": False,
    "REGISTRATION_ENABLED": True,
}
BODY = {
    "email": "ana@example.com",
    "full_name": "Ana Maria Souza",
    "password": "a-strong-password-31",
    "password_confirm": "a-strong-password-31",
}


class RegistrationWithoutVerificationTests(AccountsTestCase):
    tripaulx = OFF

    def test_registration_answers_with_a_session(self):
        resp = self.anon_api_client().post("/api/auth/register/", BODY, format="json")
        assert resp.status_code == 201, resp.data
        assert resp.data["email_verification_required"] is False
        session = resp.data["session"]
        assert session["user"]["email_verified"] is True
        assert mail.outbox == []
        client = self.anon_api_client()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {session['access']}")
        assert client.get(ME).data["email"] == "ana@example.com"

    def test_unverified_user_is_not_sent_to_the_code_screen(self):
        user = self.make_user(email="old@example.com", password="x-strong-pass-19")
        resp = self.login(user, password="x-strong-pass-19")
        assert resp.status_code == 200
        assert resp.data["mfa_required"] is True


@pytest.mark.django_db
@override_settings(TRIPAULX=OFF)
def test_signup_logs_the_owner_into_the_new_workspace(public_schema):
    public, _created = bootstrap.ensure_public()
    bootstrap.ensure_domain("sdk.test", public, primary=False)
    client = APIClient(HTTP_HOST="sdk.test:8000")
    body = {**BODY, "workspace_name": "Acme Ltda"}
    resp = client.post("/api/auth/signup/", body, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["email_verification_required"] is False
    assert mail.outbox == []
    with schema_context("acme_ltda"):
        assert get_user_model().objects.get().email_verified
    # The tokens belong to the new workspace, not to the public schema.
    workspace = APIClient(HTTP_HOST="acme-ltda.sdk.test:8000")
    access = resp.data["session"]["access"]
    workspace.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert workspace.get(ME).data["role"] == "owner"
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert client.get(ME).status_code == 401
