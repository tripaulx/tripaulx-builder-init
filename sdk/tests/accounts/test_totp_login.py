"""Login with an active app: app code, no e-mail, anti-replay, disable."""

from django.core import mail

from tripaulx.accounts.models import TotpDevice
from tripaulx.accounts.services import recovery_codes, totp

from .helpers import LOGIN_RESEND, AccountsTestCase

DISABLE = "/api/auth/totp/disable/"


class TotpTestCase(AccountsTestCase):
    def setUp(self):
        self.user = self.verified_user()
        self.secret = totp.begin_setup(self.user).secret
        totp.confirm_setup(self.user, totp.code_at(self.secret))
        # Confirming consumed the current step; reset the anti-replay guard so
        # the tests can use the same step at login.
        TotpDevice.objects.filter(user=self.user).update(last_step=0)
        mail.outbox = []


class TotpLoginTests(TotpTestCase):
    def test_login_asks_for_the_app_and_sends_no_mail(self):
        resp = self.login(self.user)
        assert resp.status_code == 200
        assert resp.data["mfa_method"] == "totp"
        assert "masked_email" not in resp.data
        assert "access" not in resp.data
        assert mail.outbox == []

    def test_app_code_completes(self):
        ticket = self.login(self.user).data["ticket"]
        resp = self.verify(ticket, totp.code_at(self.secret))
        assert resp.status_code == 200
        assert "access" in resp.data

    def test_same_code_never_works_twice(self):
        code = totp.code_at(self.secret)
        assert (
            self.verify(self.login(self.user).data["ticket"], code).status_code == 200
        )
        second = self.verify(self.login(self.user).data["ticket"], code)
        assert second.status_code == 400
        assert "already used" in second.data["detail"]

    def test_wrong_code_is_400(self):
        ticket = self.login(self.user).data["ticket"]
        assert self.verify(ticket, "000000").status_code == 400

    def test_recovery_code_also_completes(self):
        code = recovery_codes.generate_codes(self.user, 1)[0]
        resp = self.verify(self.login(self.user).data["ticket"], code)
        assert resp.status_code == 200
        assert resp.data["recovery_code_used"] is True

    def test_resend_sends_no_mail_to_app_users(self):
        ticket = self.login(self.user).data["ticket"]
        resp = self.anon_api_client().post(LOGIN_RESEND, {"ticket": ticket})
        assert resp.status_code == 200
        assert mail.outbox == []

    def test_trusted_device_skips_the_app(self):
        ticket = self.login(self.user).data["ticket"]
        first = self.verify(ticket, totp.code_at(self.secret), trust_device=True)
        token = first.data["device_token"]
        assert first.data["device_token_max_age"] == 30 * 24 * 60 * 60
        resp = self.login(self.user, device_token=token)
        assert "access" in resp.data


class TotpDisableTests(TotpTestCase):
    def setUp(self):
        super().setUp()
        self.client = self.api_client(self.user)

    def test_invalid_code_does_not_disable(self):
        assert self.client.post(DISABLE, {"code": "000000"}).status_code == 400
        assert totp.is_enabled(self.user)

    def test_app_code_disables_and_login_falls_back_to_email(self):
        resp = self.client.post(DISABLE, {"code": totp.code_at(self.secret)})
        assert resp.status_code == 200
        assert resp.data["enabled"] is False
        assert not TotpDevice.all_objects.filter(user=self.user).exists()
        assert self.login(self.user).data["mfa_method"] == "email"
        assert mail.outbox

    def test_recovery_code_disables(self):
        code = recovery_codes.generate_codes(self.user, 1)[0]
        assert self.client.post(DISABLE, {"code": code}).status_code == 200
        assert not totp.is_enabled(self.user)

    def test_disable_when_inactive_is_400(self):
        TotpDevice.objects.filter(user=self.user).delete()
        assert self.client.post(DISABLE, {"code": "123456"}).status_code == 400
