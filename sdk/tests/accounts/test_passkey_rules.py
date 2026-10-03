"""Passkey-only login, its safety rules, rename and passkey login checks."""

from unittest import mock

from tripaulx.accounts.models import WebAuthnCredential
from tripaulx.accounts.services import passkeys

from .helpers import ME, AccountsTestCase, make_passkey

TOGGLE = "/api/auth/passkey/password-login/"
CREDENTIALS = "/api/auth/passkey/credentials/"
COMPLETE = "/api/auth/passkey/login/complete/"
VERIFY = "tripaulx.accounts.services.passkeys.verify_authentication"


class PasskeyOnlyTests(AccountsTestCase):
    def setUp(self):
        self.user = self.verified_user()
        self.client = self.api_client(self.user)

    def test_turning_off_requires_a_passkey(self):
        resp = self.client.post(TOGGLE, {"disabled": True}, format="json")
        assert resp.status_code == 400
        assert "passkey" in resp.data["detail"].lower()
        self.user.refresh_from_db()
        assert not self.user.password_login_disabled

    def test_toggle_with_a_passkey(self):
        make_passkey(self.user)
        resp = self.client.post(TOGGLE, {"disabled": True}, format="json")
        assert resp.status_code == 200
        assert resp.data["password_login_disabled"] is True
        assert self.client.get(ME).data["password_login_disabled"] is True
        resp = self.client.post(TOGGLE, {"disabled": False}, format="json")
        assert resp.data["password_login_disabled"] is False

    def test_password_login_refused_with_passkey_required(self):
        make_passkey(self.user)
        passkeys.set_password_login_disabled(self.user, True)
        resp = self.login(self.user)
        assert resp.status_code == 403
        assert resp.data["passkey_required"] is True
        assert "access" not in resp.data and "ticket" not in resp.data

    def test_wrong_password_stays_401_and_hides_the_mode(self):
        make_passkey(self.user)
        passkeys.set_password_login_disabled(self.user, True)
        resp = self.login(self.user, password="wrong")
        assert resp.status_code == 401
        assert "passkey_required" not in resp.data

    def test_without_passkeys_the_password_works_again(self):
        make_passkey(self.user)
        passkeys.set_password_login_disabled(self.user, True)
        WebAuthnCredential.objects.filter(user=self.user).delete()
        assert self.login(self.user).data["mfa_required"] is True

    def test_last_passkey_cannot_go_while_password_is_off(self):
        key = make_passkey(self.user)
        passkeys.set_password_login_disabled(self.user, True)
        assert self.client.delete(f"{CREDENTIALS}{key.pk}/").status_code == 400
        assert WebAuthnCredential.objects.filter(pk=key.pk).exists()

    def test_second_to_last_goes_and_last_goes_with_password_on(self):
        first = make_passkey(self.user, "cred-a")
        second = make_passkey(self.user, "cred-b")
        passkeys.set_password_login_disabled(self.user, True)
        assert self.client.delete(f"{CREDENTIALS}{first.pk}/").status_code == 204
        assert self.client.delete(f"{CREDENTIALS}{second.pk}/").status_code == 400
        passkeys.set_password_login_disabled(self.user, False)
        assert self.client.delete(f"{CREDENTIALS}{second.pk}/").status_code == 204
        assert not WebAuthnCredential.all_objects.filter(user=self.user).exists()

    def test_cannot_remove_another_users_passkey(self):
        other = self.make_user(email="other@example.com")
        foreign = make_passkey(other, "cred-foreign")
        assert self.client.delete(f"{CREDENTIALS}{foreign.pk}/").status_code == 204
        assert WebAuthnCredential.objects.filter(pk=foreign.pk).exists()

    def test_rename_and_list(self):
        key = make_passkey(self.user)
        url = f"{CREDENTIALS}{key.pk}/"
        resp = self.client.patch(url, {"name": "Laptop"}, format="json")
        assert resp.status_code == 200
        assert resp.data["name"] == "Laptop"
        listed = self.client.get(CREDENTIALS).data["passkeys"]
        assert [p["name"] for p in listed] == ["Laptop"]

    def test_rename_another_users_passkey_is_404(self):
        foreign = make_passkey(self.make_user(email="other@example.com"), "c-x")
        url = f"{CREDENTIALS}{foreign.pk}/"
        assert self.client.patch(url, {"name": "Mine"}).status_code == 404


class PasskeyLoginTests(AccountsTestCase):
    def _complete(self, user):
        stored = make_passkey(user)
        with mock.patch(VERIFY, return_value=stored):
            return self.anon_api_client().post(
                COMPLETE, {"ticket": "t", "credential": {"id": "cred-1"}}, format="json"
            )

    def test_passkey_login_returns_tokens(self):
        resp = self._complete(self.verified_user())
        assert resp.status_code == 200
        assert "access" in resp.data

    def test_passkey_login_requires_a_verified_email(self):
        user = self.make_user(email="new@example.com")
        resp = self._complete(user)
        assert resp.status_code == 403
        assert resp.data["email_verification_required"] is True
        assert "access" not in resp.data
