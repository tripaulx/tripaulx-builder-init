"""Trusted devices: skip the 2FA, list and revoke."""

from datetime import timedelta

from django.utils import timezone

from tripaulx.accounts.models import TrustedDevice

from .helpers import AccountsTestCase, code_from_mail

DEVICES = "/api/auth/devices/"


class TrustedDeviceTests(AccountsTestCase):
    def setUp(self):
        self.user = self.verified_user()

    def _trust(self):
        ticket = self.login(self.user).data["ticket"]
        resp = self.verify(
            ticket, code_from_mail(), trust_device=True, device_label="Laptop"
        )
        return resp.data["device_token"]

    def test_token_skips_the_email_code(self):
        token = self._trust()
        resp = self.login(self.user, device_token=token)
        assert "access" in resp.data
        device = TrustedDevice.objects.get(user=self.user)
        assert device.last_used_at is not None
        assert token not in device.token_hash

    def test_expired_token_falls_back_to_2fa(self):
        token = self._trust()
        TrustedDevice.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        assert self.login(self.user, device_token=token).data["mfa_required"] is True

    def test_token_of_another_user_is_ignored(self):
        token = self._trust()
        other = self.verified_user(email="other@example.com")
        assert self.login(other, device_token=token).data["mfa_required"] is True

    def test_list_and_revoke(self):
        token = self._trust()
        client = self.api_client(self.user)
        listed = client.get(DEVICES).data["results"]
        assert [d["device_label"] for d in listed] == ["Laptop"]
        assert "token_hash" not in listed[0]
        assert client.delete(f"{DEVICES}{listed[0]['id']}/").status_code == 204
        assert client.get(DEVICES).data["results"] == []
        assert self.login(self.user, device_token=token).data["mfa_required"] is True

    def test_cannot_revoke_another_users_device(self):
        self._trust()
        device = TrustedDevice.objects.get(user=self.user)
        other = self.api_client(self.verified_user(email="other@example.com"))
        assert other.delete(f"{DEVICES}{device.pk}/").status_code == 404
        device.refresh_from_db()
        assert device.is_active
