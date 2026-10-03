"""Authenticator setup: setup -> confirm -> status, and what each must not do."""

from tripaulx.accounts.models import TotpDevice
from tripaulx.accounts.services import totp

from .helpers import AccountsTestCase

STATUS = "/api/auth/totp/"
SETUP = "/api/auth/totp/setup/"
CONFIRM = "/api/auth/totp/confirm/"


class TotpSetupTests(AccountsTestCase):
    def setUp(self):
        self.user = self.verified_user()
        self.client = self.api_client(self.user)

    def _setup(self):
        return self.client.post(SETUP, {}, format="json")

    def test_status_starts_disabled(self):
        resp = self.client.get(STATUS)
        assert resp.status_code == 200
        assert resp.data == {
            "enabled": False,
            "confirmed_at": None,
            "recovery_codes_remaining": 0,
        }

    def test_setup_returns_secret_uri_qr_and_stores_it_encrypted(self):
        resp = self._setup()
        assert resp.status_code == 200
        secret = resp.data["secret"]
        assert f"secret={secret}" in resp.data["otpauth_uri"]
        assert "Acme" in resp.data["otpauth_uri"]
        assert "<svg" in resp.data["qr_svg"]
        device = TotpDevice.objects.get(user=self.user)
        assert not device.confirmed
        assert secret not in device.secret_encrypted
        assert device.secret == secret
        assert self.client.get(STATUS).data["enabled"] is False

    def test_setup_again_replaces_the_pending_secret(self):
        first = self._setup().data["secret"]
        second = self._setup().data["secret"]
        assert first != second
        assert TotpDevice.objects.filter(user=self.user).count() == 1

    def test_wrong_code_does_not_confirm(self):
        self._setup()
        assert self.client.post(CONFIRM, {"code": "000000"}).status_code == 400
        assert not totp.is_enabled(self.user)

    def test_confirm_enables_and_shows_recovery_codes_once(self):
        secret = self._setup().data["secret"]
        resp = self.client.post(CONFIRM, {"code": totp.code_at(secret)})
        assert resp.status_code == 201
        assert resp.data["enabled"] is True
        assert resp.data["confirmed_at"] is not None
        assert len(resp.data["recovery_codes"]) == 9
        assert resp.data["recovery_codes_remaining"] == 9
        status = self.client.get(STATUS)
        assert "recovery_codes" not in status.data
        assert secret not in status.content.decode()

    def test_confirm_without_pending_setup_is_400(self):
        assert self.client.post(CONFIRM, {"code": "123456"}).status_code == 400

    def test_setup_is_refused_while_active(self):
        secret = self._setup().data["secret"]
        self.client.post(CONFIRM, {"code": totp.code_at(secret)})
        assert self._setup().status_code == 400
        assert TotpDevice.objects.get(user=self.user).secret == secret

    def test_cancel_removes_only_the_pending_device(self):
        self._setup()
        assert self.client.delete(SETUP).status_code == 204
        assert not TotpDevice.objects.filter(user=self.user).exists()

    def test_requires_authentication(self):
        anon = self.anon_api_client()
        assert anon.get(STATUS).status_code == 401
        assert anon.post(SETUP, {}).status_code == 401
