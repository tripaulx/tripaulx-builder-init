"""Login always ends with a second factor (e-mail code without an app)."""

from django.core import mail

from tripaulx.accounts.models import EmailCode, EmailCodePurpose
from tripaulx.accounts.signals import user_logged_in_2fa

from .helpers import LOGIN_RESEND, AccountsTestCase, code_from_mail


class MandatorySecondFactorTests(AccountsTestCase):
    def setUp(self):
        self.user = self.verified_user()

    def test_login_requires_2fa_and_returns_no_token(self):
        resp = self.login(self.user)
        assert resp.status_code == 200
        assert resp.data["mfa_required"] is True
        assert resp.data["mfa_method"] == "email"
        assert resp.data["masked_email"] == "j***e@example.com"
        assert "ticket" in resp.data
        assert "access" not in resp.data
        assert mail.outbox, "a 2FA code should have been sent"

    def test_2fa_mail_has_html_alternative_and_brand(self):
        self.login(self.user)
        message = mail.outbox[-1]
        assert message.subject == "Acme · Your access code"
        code = code_from_mail()
        html, mimetype = message.alternatives[0]
        assert mimetype == "text/html"
        assert " ".join(code) in html
        assert "Acme" in html

    def test_verify_completes_with_the_code(self):
        received = []
        user_logged_in_2fa.connect(
            lambda **kw: received.append(kw["method"]), weak=False, dispatch_uid="t"
        )
        try:
            ticket = self.login(self.user).data["ticket"]
            resp = self.verify(ticket, code_from_mail())
        finally:
            user_logged_in_2fa.disconnect(dispatch_uid="t")
        assert resp.status_code == 200
        assert {"access", "refresh"} <= set(resp.data)
        assert resp.data["user"]["email"] == self.user.email
        assert received == ["email"]
        self.user.refresh_from_db()
        assert self.user.last_login is not None

    def test_wrong_code_is_400(self):
        ticket = self.login(self.user).data["ticket"]
        assert self.verify(ticket, "000000").status_code == 400

    def test_bad_ticket_is_400(self):
        resp = self.verify("forged:ticket", "123456")
        assert resp.status_code == 400
        assert "access" not in resp.data

    def test_resend_issues_a_new_code(self):
        ticket = self.login(self.user).data["ticket"]
        # Simulate the cooldown having passed.
        EmailCode.all_objects.filter(
            user=self.user, purpose=EmailCodePurpose.LOGIN_2FA
        ).delete()
        mail.outbox = []
        resp = self.anon_api_client().post(
            LOGIN_RESEND, {"ticket": ticket}, format="json"
        )
        assert resp.status_code == 200
        assert mail.outbox
        assert self.verify(ticket, code_from_mail()).status_code == 200

    def test_resend_respects_the_cooldown(self):
        ticket = self.login(self.user).data["ticket"]
        mail.outbox = []
        self.anon_api_client().post(LOGIN_RESEND, {"ticket": ticket}, format="json")
        assert mail.outbox == []

    def test_wrong_password_is_401(self):
        resp = self.login(self.user, password="wrong")
        assert resp.status_code == 401

    def test_email_lookup_ignores_case(self):
        resp = self.anon_api_client().post(
            "/api/auth/login/",
            {"email": "JANE@example.com", "password": "correct-horse-battery-42"},
            format="json",
        )
        assert resp.data["mfa_required"] is True

    def test_unverified_email_asks_for_confirmation(self):
        other = self.make_user(
            email="new@example.com", password="correct-horse-battery-42"
        )
        resp = self.login(other)
        assert resp.status_code == 403
        assert resp.data["email_verification_required"] is True
        assert "ticket" not in resp.data

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        assert self.login(self.user).status_code == 401


class CodeAttemptTests(AccountsTestCase):
    def test_code_locks_after_max_attempts(self):
        user = self.verified_user()
        ticket = self.login(user).data["ticket"]
        code = code_from_mail()
        for _ in range(5):
            assert self.verify(ticket, "000000").status_code == 400
        resp = self.verify(ticket, code)
        assert resp.status_code == 400
        assert "access" not in resp.data
