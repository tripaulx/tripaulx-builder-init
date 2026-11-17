"""Public configuration of the auth screens and workspace lookup by slug."""

from django.test import override_settings
import pytest
from rest_framework.test import APIClient

from tripaulx.tenants.models import Workspace
from tripaulx.tenants.services import bootstrap

from .helpers import AccountsTestCase

CONFIG = "/api/auth/config/"
LOOKUP = "/api/auth/workspaces/{}/"
pytestmark = pytest.mark.django_db


@pytest.fixture
def public_client(public_schema):
    public, _created = bootstrap.ensure_public()
    bootstrap.ensure_domain("sdk.test", public, primary=False)
    return APIClient(HTTP_HOST="sdk.test:8000")


def test_public_config_defaults(public_client):
    assert public_client.get(CONFIG).data == {
        "signup_enabled": True,
        "registration_enabled": False,
        "registration_profiles": [],
        "registration_fields": (),
        "email_verification_required": True,
        "email_available": True,
        "mfa_policy": "always",
        "base_domain": "sdk.test",
        "workspace_origin_template": "http://{subdomain}.sdk.test:8000",
    }


def test_lookup_tells_free_reserved_and_invalid_slugs(public_client):
    free = public_client.get(LOOKUP.format("acme")).data
    assert (free["exists"], free["available"], free["api_url"]) == (False, True, "")
    for slug in ("www", "Bad-Slug!"):
        data = public_client.get(LOOKUP.format(slug)).data
        assert (data["exists"], data["available"]) == (False, False)
        assert data["reason"]


def test_lookup_finds_an_active_workspace(public_client):
    workspace = Workspace(schema_name="acme_co", name="Acme Co")
    workspace.auto_create_schema = False
    workspace.save()
    data = public_client.get(LOOKUP.format("ACME_CO")).data
    assert data["exists"] is True and data["available"] is False
    assert data["name"] == "Acme Co"
    assert data["api_url"] == "http://acme-co.sdk.test:8000/api"
    Workspace.objects.filter(pk=workspace.pk).update(is_active=False)
    data = public_client.get(LOOKUP.format("acme_co")).data
    assert (data["exists"], data["available"], data["name"]) == (False, False, "")


class WorkspaceSideTests(AccountsTestCase):
    def test_lookup_only_exists_on_the_public_schema(self):
        assert self.anon_api_client().get(LOOKUP.format("acme")).status_code == 404

    def test_signup_is_never_offered_inside_a_workspace(self):
        assert self.anon_api_client().get(CONFIG).data["signup_enabled"] is False

    @override_settings(TRIPAULX={"MFA_POLICY": "privileged"})
    def test_config_follows_the_settings(self):
        assert self.anon_api_client().get(CONFIG).data["mfa_policy"] == "privileged"
