"""The RP ID and origins come from the request host (setting wins when set)."""

from django.test import RequestFactory, override_settings

from tripaulx.accounts.services import passkeys

from .helpers import AccountsTestCase

REGISTER_BEGIN = "/api/auth/passkey/register/begin/"
LOGIN_BEGIN = "/api/auth/passkey/login/begin/"


def _request(host):
    return RequestFactory().get("/", HTTP_HOST=host)


@override_settings(ALLOWED_HOSTS=["*"])
def test_rp_id_is_the_host_without_port():
    assert passkeys.rp_id_for(_request("acme.example.localhost:8000")) == (
        "acme.example.localhost"
    )


@override_settings(ALLOWED_HOSTS=["*"], TRIPAULX={"WEBAUTHN_RP_ID": "example.com"})
def test_configured_rp_id_wins():
    assert passkeys.rp_id_for(_request("acme.example.com")) == "example.com"


@override_settings(
    ALLOWED_HOSTS=["*"],
    TRIPAULX={
        "WEBAUTHN_ORIGINS": (
            "http://localhost:5173",
            "http://acme.example.localhost:8000",
        )
    },
)
def test_own_origin_first_then_extras():
    origins = passkeys.expected_origins_for(_request("acme.example.localhost:8000"))
    assert origins == ["http://acme.example.localhost:8000", "http://localhost:5173"]


@override_settings(TRIPAULX={"APP_NAME": "Acme", "WEBAUTHN_RP_NAME": ""})
def test_rp_name_defaults_to_app_name():
    assert passkeys.rp_name() == "Acme"


class CeremonyHostTests(AccountsTestCase):
    def test_register_and_login_use_the_workspace_host(self):
        domain = self.tenant.get_primary_domain().domain
        begin = self.api_client(self.verified_user()).post(REGISTER_BEGIN)
        assert begin.status_code == 200
        assert begin.data["rp"]["id"] == domain
        assert begin.data["rp"]["name"] == "Acme"
        login = self.anon_api_client().post(LOGIN_BEGIN, {"email": ""})
        assert login.status_code == 200
        assert login.data["options"]["rpId"] == domain
        assert login.data["ticket"]

    def test_login_begin_with_email_lists_the_users_credentials(self):
        from .helpers import make_passkey

        user = self.verified_user()
        make_passkey(user, "AAAA")
        resp = self.anon_api_client().post(LOGIN_BEGIN, {"email": user.email})
        assert [c["id"] for c in resp.data["options"]["allowCredentials"]] == ["AAAA"]

    def test_complete_with_unknown_ticket_is_400(self):
        resp = self.anon_api_client().post(
            "/api/auth/passkey/login/complete/",
            {"ticket": "nope", "credential": {"id": "x"}},
            format="json",
        )
        assert resp.status_code == 400
