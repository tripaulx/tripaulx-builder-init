"""Recovery codes: format, single use, replacement, login and API."""

import pytest

from tripaulx.accounts.models import RecoveryCode
from tripaulx.accounts.services import recovery_codes
from tripaulx.accounts.services.errors import RecoveryCodeError

from .helpers import AccountsTestCase, code_from_mail

API = "/api/auth/mfa/recovery-codes/"


class RecoveryCodeServiceTests(AccountsTestCase):
    def setUp(self):
        self.user = self.make_user()

    def test_generates_distinct_codes_and_stores_only_hashes(self):
        codes = recovery_codes.generate_codes(self.user, 9)
        assert len(set(codes)) == 9
        assert RecoveryCode.objects.filter(user=self.user).count() == 9
        for code in codes:
            assert len(code) == 11 and code[5] == "-"
            assert not RecoveryCode.objects.filter(code_hash=code).exists()

    def test_a_code_works_once(self):
        codes = recovery_codes.generate_codes(self.user, 9)
        assert recovery_codes.verify_code(self.user, codes[0]).is_used
        assert recovery_codes.remaining(self.user) == 8
        with pytest.raises(RecoveryCodeError):
            recovery_codes.verify_code(self.user, codes[0])

    def test_typed_without_dash_and_lowercase(self):
        code = recovery_codes.generate_codes(self.user, 9)[0]
        recovery_codes.verify_code(self.user, code.replace("-", "").lower())
        assert recovery_codes.remaining(self.user) == 8

    def test_new_list_burns_the_old_one(self):
        old = recovery_codes.generate_codes(self.user, 9)
        new = recovery_codes.generate_codes(self.user, 9)
        assert recovery_codes.remaining(self.user) == 9
        with pytest.raises(RecoveryCodeError):
            recovery_codes.verify_code(self.user, old[0])
        recovery_codes.verify_code(self.user, new[0])

    def test_another_users_code_does_not_work(self):
        other = self.make_user(email="other@example.com")
        code = recovery_codes.generate_codes(other, 9)[0]
        with pytest.raises(RecoveryCodeError):
            recovery_codes.verify_code(self.user, code)

    def test_otp_is_not_mistaken_for_a_recovery_code(self):
        assert not recovery_codes.looks_like_recovery_code("123456")
        assert recovery_codes.looks_like_recovery_code("ABCD2-3EFGH")


class RecoveryCodeLoginTests(AccountsTestCase):
    def setUp(self):
        self.user = self.verified_user()
        self.codes = recovery_codes.generate_codes(self.user, 9)

    def _ticket(self):
        return self.login(self.user).data["ticket"]

    def test_completes_login_without_the_email_code(self):
        resp = self.verify(self._ticket(), self.codes[0])
        assert resp.status_code == 200
        assert resp.data["recovery_code_used"] is True
        assert resp.data["recovery_codes_remaining"] == 8

    def test_same_code_fails_the_second_time(self):
        assert self.verify(self._ticket(), self.codes[0]).status_code == 200
        resp = self.verify(self._ticket(), self.codes[0])
        assert resp.status_code == 400
        assert "access" not in resp.data

    def test_wrong_recovery_code_is_refused(self):
        assert self.verify(self._ticket(), "ZZZZZ-ZZZZZ").status_code == 400

    def test_email_code_still_works(self):
        ticket = self._ticket()
        resp = self.verify(ticket, code_from_mail())
        assert resp.status_code == 200
        assert "recovery_code_used" not in resp.data
        assert recovery_codes.remaining(self.user) == 9


class RecoveryCodeApiTests(AccountsTestCase):
    def test_post_generates_and_get_counts(self):
        client = self.api_client(self.verified_user())
        resp = client.post(API, {"quantity": 5}, format="json")
        assert resp.status_code == 201
        assert len(resp.data["codes"]) == 5
        assert client.get(API).data["remaining"] == 5

    def test_default_quantity_is_nine(self):
        client = self.api_client(self.verified_user())
        assert len(client.post(API, {}, format="json").data["codes"]) == 9

    def test_anonymous_is_refused(self):
        assert self.anon_api_client().get(API).status_code == 401
