"""Every account passes a second factor; privileged ones need a strong one.

Owners, admins and staff without an app or a passkey get
``mfa_setup_required`` so clients can ask them to set one up.
"""

from django.core import mail

from tripaulx.accounts.models import Role
from tripaulx.accounts.services import totp

from .helpers import ME, AccountsTestCase, make_passkey


class PrivilegedMfaTests(AccountsTestCase):
    def test_member_still_gets_the_second_factor(self):
        user = self.verified_user()
        resp = self.login(user)
        assert resp.data["mfa_required"] is True
        assert "access" not in resp.data
        assert self.api_client(user).get(ME).data["mfa_setup_required"] is False

    def test_staff_without_strong_factor_gets_email_code(self):
        user = self.verified_user(is_staff=True)
        resp = self.login(user)
        assert resp.data["mfa_method"] == "email"
        assert mail.outbox
        assert self.api_client(user).get(ME).data["mfa_setup_required"] is True

    def test_owner_without_strong_factor_must_set_one_up(self):
        user = self.verified_user(role=Role.OWNER)
        assert self.api_client(user).get(ME).data["mfa_setup_required"] is True

    def test_staff_with_app_uses_it(self):
        user = self.verified_user(is_staff=True)
        secret = totp.begin_setup(user).secret
        totp.confirm_setup(user, totp.code_at(secret))
        mail.outbox = []
        assert self.login(user).data["mfa_method"] == "totp"
        assert mail.outbox == []
        assert self.api_client(user).get(ME).data["mfa_setup_required"] is False

    def test_admin_with_passkey_is_fine(self):
        user = self.verified_user(role=Role.ADMIN)
        make_passkey(user)
        me = self.api_client(user).get(ME).data
        assert me["mfa_setup_required"] is False
        assert me["is_workspace_admin"] is True
