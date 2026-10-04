"""Signup on the public schema creates a workspace and its unverified owner."""

import re

from django.core import mail
from django.test import override_settings
from django_tenants.utils import schema_context
import pytest
from rest_framework.test import APIClient

from tripaulx.accounts.models import Role
from tripaulx.tenants.models import Domain, Workspace
from tripaulx.tenants.services import bootstrap

pytestmark = pytest.mark.django_db
SIGNUP = "/api/auth/signup/"
BODY = {
    "email": "Owner@Example.com",
    "full_name": "Ana Maria Souza",
    "password": "a-strong-password-31",
    "password_confirm": "a-strong-password-31",
    "workspace_name": "Acme Ltda",
}


@pytest.fixture
def public_client(public_schema):
    public, _created = bootstrap.ensure_public()
    bootstrap.ensure_domain("sdk.test", public, primary=False)
    return APIClient(HTTP_HOST="sdk.test:8000")


def test_signup_creates_workspace_domain_and_owner(public_client):
    resp = public_client.post(SIGNUP, BODY, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data == {
        "workspace_slug": "acme_ltda",
        "workspace_domain": "acme-ltda.sdk.test",
        "workspace_url": "http://acme-ltda.sdk.test:8000",
        "email": "Owner@example.com",
        "email_verification_required": True,
    }
    workspace = Workspace.objects.get(schema_name="acme_ltda")
    assert workspace.name == "Acme Ltda"
    assert Domain.objects.get(tenant=workspace).domain == "acme-ltda.sdk.test"
    with schema_context("acme_ltda"):
        from django.contrib.auth import get_user_model

        owner = get_user_model().objects.get()
        assert owner.role == Role.OWNER
        assert not owner.email_verified
        assert (owner.first_name, owner.last_name) == ("Ana", "Maria Souza")
    assert re.search(r"\b\d{6}\b", mail.outbox[-1].body)
    assert mail.outbox[-1].to == ["Owner@example.com"]


def test_explicit_slug_and_taken_slug(public_client):
    body = {**BODY, "slug": "acme"}
    assert public_client.post(SIGNUP, body, format="json").status_code == 201
    again = public_client.post(SIGNUP, body, format="json")
    assert again.status_code == 400
    assert again.data["field"] == "slug"


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"slug": "www"}, "slug"),
        ({"slug": "Bad-Slug"}, "slug"),
        ({"password": "123", "password_confirm": "123"}, "password"),
        ({"password_confirm": "another-strong-pass-77"}, "password_confirm"),
        ({"full_name": "   "}, "full_name"),
        # Too similar to the person: validated against the e-mail and name.
        (
            {"password": "anamariasouza", "password_confirm": "anamariasouza"},
            "password",
        ),
        ({"workspace_name": "  "}, None),
    ],
)
def test_invalid_input_creates_nothing(public_client, override, field):
    resp = public_client.post(SIGNUP, {**BODY, **override}, format="json")
    assert resp.status_code == 400
    if field:
        assert resp.data["field"] == field
    assert (
        not Workspace.objects.exclude(schema_name="public")
        .filter(name="Acme Ltda")
        .exists()
    )


def test_signup_can_be_disabled(public_client):
    with override_settings(TRIPAULX={"SIGNUP_ENABLED": False}):
        assert public_client.post(SIGNUP, BODY, format="json").status_code == 403


def test_signup_is_throttled(public_client):
    for _ in range(5):
        public_client.post(SIGNUP, {**BODY, "slug": "www"}, format="json")
    assert public_client.post(SIGNUP, BODY, format="json").status_code == 429
