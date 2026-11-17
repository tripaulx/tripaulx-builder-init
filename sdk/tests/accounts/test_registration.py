"""Self-service registration creates a member inside the workspace."""

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings

from tripaulx.accounts.models import Role
from tripaulx.accounts.signals import user_registered

from .helpers import AccountsTestCase, code_from_mail

REGISTER = "/api/auth/register/"
VERIFY = "/api/auth/email/verify/"
ON = {"APP_NAME": "Acme", "BASE_DOMAIN": "sdk.test", "REGISTRATION_ENABLED": True}
BODY = {
    "email": "Ana@Example.com",
    "full_name": "Ana Maria Souza",
    "password": "a-strong-password-31",
    "password_confirm": "a-strong-password-31",
}


class RegistrationTests(AccountsTestCase):
    def post(self, **override):
        body = {**BODY, **override}
        return self.anon_api_client().post(REGISTER, body, format="json")

    def test_disabled_by_default(self):
        assert self.post().status_code == 403
        assert not get_user_model().objects.exists()

    @override_settings(TRIPAULX=ON)
    def test_creates_an_unverified_member_and_sends_the_code(self):
        resp = self.post()
        assert resp.status_code == 201, resp.data
        assert resp.data == {
            "email": "Ana@example.com",
            "profile": "",
            "email_verification_required": True,
            "session": None,
        }
        user = get_user_model().objects.get()
        assert user.role == Role.MEMBER
        assert not user.email_verified and not user.is_staff
        assert (user.first_name, user.last_name) == ("Ana", "Maria Souza")
        assert mail.outbox[-1].to == ["Ana@example.com"]

    @override_settings(TRIPAULX=ON)
    def test_the_code_verifies_and_logs_in(self):
        self.post()
        body = {"email": "ana@example.com", "code": code_from_mail()}
        resp = self.anon_api_client().post(VERIFY, body, format="json")
        assert resp.status_code == 200
        assert {"access", "refresh"} <= set(resp.data)
        assert resp.data["user"]["email_verified"] is True

    @override_settings(TRIPAULX=ON)
    def test_invalid_input_creates_nothing(self):
        cases = [
            ({"full_name": "  "}, "full_name"),
            ({"password": "123", "password_confirm": "123"}, "password"),
            ({"password_confirm": "another-strong-pass-77"}, "password_confirm"),
        ]
        for override, field in cases:
            resp = self.post(**override)
            assert resp.status_code == 400
            assert resp.data["field"] == field
        assert not get_user_model().objects.exists()

    @override_settings(TRIPAULX=ON)
    def test_existing_verified_account_is_refused(self):
        self.verified_user(email="ana@example.com")
        mail.outbox = []
        resp = self.post()
        assert resp.status_code == 400
        assert resp.data["field"] == "email"
        assert "email_verification_required" not in resp.data
        assert mail.outbox == []

    @override_settings(TRIPAULX={**ON, "OTP_RESEND_COOLDOWN": 0})
    def test_pending_account_gets_a_new_code_instead_of_a_dead_end(self):
        self.post()
        other = "other-strong-pass-55"
        resp = self.post(password=other, password_confirm=other)
        assert resp.status_code == 400
        assert resp.data["email_verification_required"] is True
        assert len(mail.outbox) == 2
        # The second attempt never replaces the first password.
        user = get_user_model().objects.get()
        assert user.check_password(BODY["password"])

    @override_settings(TRIPAULX=ON)
    def test_sends_the_signal(self):
        received = []
        user_registered.connect(
            lambda **kw: received.append(kw["user"].email),
            weak=False,
            dispatch_uid="t",
        )
        try:
            self.post()
        finally:
            user_registered.disconnect(dispatch_uid="t")
        assert received == ["Ana@example.com"]

    @override_settings(TRIPAULX=ON)
    def test_is_throttled(self):
        for _ in range(5):
            self.post(full_name="")
        assert self.post().status_code == 429
