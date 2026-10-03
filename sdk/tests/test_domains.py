from django.test import override_settings

from tripaulx.tenants.services.domains import public_domains, workspace_domain


def test_workspace_domain_uses_dashes():
    assert workspace_domain("acme_co") == "acme-co.sdk.test"
    assert workspace_domain("acme", "example.com") == "acme.example.com"


def test_public_domains_include_apex_www_and_extras():
    tripaulx = {"BASE_DOMAIN": "example.com", "PUBLIC_DOMAINS": ("example.com", "x")}
    with override_settings(TRIPAULX=tripaulx):
        assert public_domains() == ["example.com", "www.example.com", "x"]
