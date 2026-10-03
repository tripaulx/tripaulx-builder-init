"""E-mail verification by code."""

from django.core import mail

from tripaulx.accounts.models import EmailCode
from tripaulx.accounts.services import email_codes

from .helpers import PASSWORD, AccountsTestCase, code_from_mail

VERIFY = "/api/auth/email/verify/"
RESEND = "/api/auth/email/resend/"


class EmailVerifyTests(AccountsTestCase):
    def setUp(self):
        self.user = self.make_user(email=self.email, password=PASSWORD)
        self.client = self.anon_api_client()

    def test_login_sends_code_and_verify_logs_in(self):
        assert self.login(self.user).status_code == 403
        resp = self.client.post(VERIFY, {"email": self.email, "code": code_from_mail()})
        assert resp.status_code == 200
        assert "access" in resp.data
        assert resp.data["user"]["email_verified"] is True

    def test_wrong_code_and_unknown_email_look_the_same(self):
        self.login(self.user)
        wrong = self.client.post(VERIFY, {"email": self.email, "code": "000000"})
        unknown = self.client.post(
            VERIFY, {"email": "nobody@example.com", "code": "000000"}
        )
        assert wrong.status_code == unknown.status_code == 400
        assert wrong.data["detail"] == unknown.data["detail"]

    def test_resend_respects_cooldown_and_is_silent(self):
        assert self.client.post(RESEND, {"email": self.email}).status_code == 200
        assert len(mail.outbox) == 1
        self.client.post(RESEND, {"email": self.email})
        assert len(mail.outbox) == 1
        resp = self.client.post(RESEND, {"email": "nobody@example.com"})
        assert resp.status_code == 200

    def test_new_code_consumes_the_previous_one(self):
        email_codes.issue_code(self.user, "email_verify")
        first = code_from_mail()
        email_codes.issue_code(self.user, "email_verify")
        resp = self.client.post(VERIFY, {"email": self.email, "code": first})
        assert resp.status_code == 400 or first == code_from_mail()
        assert EmailCode.objects.filter(consumed_at__isnull=True).count() == 1

    def test_code_is_stored_hashed(self):
        email_codes.issue_code(self.user, "email_verify")
        assert code_from_mail() not in EmailCode.objects.get().code_hash
