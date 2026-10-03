"""Password change while logged in ends the other sessions."""

from tripaulx.accounts.services import trusted_devices
from tripaulx.accounts.services.tokens import refresh_for

from .helpers import PASSWORD, REFRESH, AccountsTestCase

CHANGE = "/api/auth/password/change/"
NEW = "another-strong-password-77"


class PasswordChangeTests(AccountsTestCase):
    def setUp(self):
        self.user = self.verified_user()
        self.client = self.api_client(self.user)

    def _change(self, current=PASSWORD, new=NEW):
        body = {"current_password": current, "new_password": new}
        return self.client.post(CHANGE, body, format="json")

    def test_changes_password_and_returns_new_tokens(self):
        old_refresh = str(refresh_for(self.user))
        token = trusted_devices.issue_token(self.user, None, "Laptop")
        resp = self._change()
        assert resp.status_code == 200
        assert {"access", "refresh"} <= set(resp.data)
        self.user.refresh_from_db()
        assert self.user.check_password(NEW)
        assert trusted_devices.find_valid_device(self.user, token) is None
        anon = self.anon_api_client()
        assert anon.post(REFRESH, {"refresh": old_refresh}).status_code == 401
        assert anon.post(REFRESH, {"refresh": resp.data["refresh"]}).status_code == 200

    def test_wrong_current_password_is_400(self):
        assert self._change(current="nope").status_code == 400
        self.user.refresh_from_db()
        assert self.user.check_password(PASSWORD)

    def test_weak_new_password_is_400(self):
        assert self._change(new="123").status_code == 400

    def test_requires_authentication(self):
        resp = self.anon_api_client().post(CHANGE, {}, format="json")
        assert resp.status_code == 401
