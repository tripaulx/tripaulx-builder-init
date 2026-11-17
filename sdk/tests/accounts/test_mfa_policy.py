"""``MFA_POLICY`` decides who must pass a second factor on login."""

from django.core import mail
from django.test import override_settings

from tripaulx.accounts.models import Role
from tripaulx.accounts.services import totp
from tripaulx.accounts.signals import user_logged_in_2fa

from .helpers import AccountsTestCase


def policy(value):
    return override_settings(TRIPAULX={"APP_NAME": "Acme", "MFA_POLICY": value})


class MfaPolicyTests(AccountsTestCase):
    def setUp(self):
        super().setUp()
        self.member = self.verified_user()

    def assert_logged_in_with_password(self, user):
        mail.outbox = []
        resp = self.login(user)
        assert resp.status_code == 200
        assert {"access", "refresh"} <= set(resp.data)
        assert "mfa_required" not in resp.data
        assert mail.outbox == []

    def assert_challenged(self, user, method="email"):
        resp = self.login(user)
        assert resp.data["mfa_required"] is True
        assert resp.data["mfa_method"] == method
        assert "access" not in resp.data

    def test_default_and_unknown_values_ask_everyone(self):
        self.assert_challenged(self.member)
        with policy("allways"):
            self.assert_challenged(self.member)

    def test_privileged_spares_members_only(self):
        owner = self.verified_user(email="owner@example.com", role=Role.OWNER)
        staff = self.verified_user(email="staff@example.com", is_staff=True)
        with policy("privileged"):
            self.assert_logged_in_with_password(self.member)
            self.assert_challenged(owner)
            self.assert_challenged(staff)

    def test_optional_spares_everyone_without_an_app(self):
        owner = self.verified_user(email="owner@example.com", role=Role.OWNER)
        with policy("optional"):
            self.assert_logged_in_with_password(self.member)
            self.assert_logged_in_with_password(owner)

    def test_an_authenticator_app_is_always_asked(self):
        secret = totp.begin_setup(self.member).secret
        totp.confirm_setup(self.member, totp.code_at(secret))
        for value in ("privileged", "optional"):
            with policy(value):
                self.assert_challenged(self.member, method="totp")

    def test_wrong_password_is_still_refused(self):
        with policy("optional"):
            assert self.login(self.member, password="wrong").status_code == 401

    def test_signal_reports_the_password_method(self):
        received = []
        user_logged_in_2fa.connect(
            lambda **kw: received.append(kw["method"]), weak=False, dispatch_uid="p"
        )
        try:
            with policy("optional"):
                self.login(self.member)
        finally:
            user_logged_in_2fa.disconnect(dispatch_uid="p")
        assert received == ["password"]
