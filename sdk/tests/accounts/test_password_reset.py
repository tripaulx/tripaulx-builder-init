"""Password reset by 6-digit code, with anti-enumeration answers."""

from django.core import mail

from tripaulx.accounts.services.tokens import refresh_for

from .helpers import PASSWORD, REFRESH, AccountsTestCase, code_from_mail

RESET = "/api/auth/password/reset/"
CONFIRM = "/api/auth/password/reset/confirm/"
NEW = "new-strong-password-98"


class PasswordResetTests(AccountsTestCase):
    def setUp(self):
        self.user = self.make_user(email=self.email, password=PASSWORD)
        self.client = self.anon_api_client()

    def _confirm(self, code, password=NEW, email=None):
        body = {
            "email": email or self.email,
            "code": code,
            "password": password,
            "password_confirm": password,
        }
        return self.client.post(CONFIRM, body, format="json")

    def test_full_flow_changes_the_password(self):
        assert self.client.post(RESET, {"email": self.email}).status_code == 200
        assert self._confirm(code_from_mail()).status_code == 200
        self.user.refresh_from_db()
        assert self.user.check_password(NEW)

    def test_wrong_code_keeps_the_password(self):
        self.client.post(RESET, {"email": self.email})
        assert self._confirm("000000").status_code == 400
        self.user.refresh_from_db()
        assert self.user.check_password(PASSWORD)

    def test_unknown_email_is_silent(self):
        resp = self.client.post(RESET, {"email": "nobody@example.com"})
        assert resp.status_code == 200
        assert mail.outbox == []

    def test_weak_password_is_400(self):
        self.client.post(RESET, {"email": self.email})
        assert self._confirm(code_from_mail(), password="123").status_code == 400
        self.user.refresh_from_db()
        assert self.user.check_password(PASSWORD)

    def test_weak_password_does_not_burn_the_code(self):
        self.client.post(RESET, {"email": self.email})
        code = code_from_mail()
        assert self._confirm(code, password="123").status_code == 400
        assert self._confirm(code).status_code == 200

    def test_confirm_does_not_enumerate_accounts(self):
        known = self._confirm("000000")
        unknown = self._confirm("000000", email="nobody@example.com")
        assert known.status_code == unknown.status_code == 400
        assert known.data["detail"] == unknown.data["detail"]

    def test_reset_blacklists_existing_refresh_tokens(self):
        # ``refresh_for`` carries the schema claim: a bare RefreshToken would
        # fail for the missing claim and prove nothing about the blacklist.
        refresh = str(refresh_for(self.user))
        self.client.post(RESET, {"email": self.email})
        assert self._confirm(code_from_mail()).status_code == 200
        resp = self.client.post(REFRESH, {"refresh": refresh}, format="json")
        assert resp.status_code == 401
