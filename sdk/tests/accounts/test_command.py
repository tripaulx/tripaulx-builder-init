"""The ``generate_recovery_codes`` management command."""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
import pytest

from tripaulx.accounts.services import recovery_codes

from .helpers import AccountsTestCase


class GenerateRecoveryCodesTests(AccountsTestCase):
    def _run(self, *args):
        out = StringIO()
        call_command(
            "generate_recovery_codes",
            "--schema",
            self.tenant.schema_name,
            *args,
            stdout=out,
        )
        return out.getvalue()

    def test_prints_codes_once_and_stores_hashes(self):
        user = self.make_user(email="jane@example.com")
        output = self._run("--user", "JANE@example.com", "--quantity", "3")
        assert "3 recovery codes" in output
        assert recovery_codes.remaining(user) == 3

    def test_warns_about_the_revoked_list(self):
        self.make_user(email="jane@example.com")
        self._run("--user", "jane@example.com")
        assert "previous list revoked" in self._run("--user", "jane@example.com")

    def test_unknown_user_fails(self):
        with pytest.raises(CommandError):
            self._run("--user", "nobody@example.com")

    def test_quantity_must_be_positive(self):
        with pytest.raises(CommandError):
            self._run("--user", "x@example.com", "--quantity", "0")
