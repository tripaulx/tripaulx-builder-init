"""``create_workspace_admin``: the first administrator of a workspace."""

from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
import pytest

from tripaulx.accounts.models import Role
from tripaulx.core.testing import TenantTestCase

PASSWORD = "a-strong-password-31"


class CreateWorkspaceAdminTests(TenantTestCase):
    def _run(self, *args, stdin=PASSWORD + "\n"):
        out = StringIO()
        with mock.patch("sys.stdin", StringIO(stdin)):
            call_command(
                "create_workspace_admin",
                "--schema",
                connection.schema_name,
                *args,
                stdout=out,
                stderr=out,
            )
        return out.getvalue()

    def test_creates_a_verified_owner_with_admin_access(self):
        out = self._run(
            "--email", "Ana@Example.com", "--full-name", "Ana Souza", "--password-stdin"
        )
        user = get_user_model().objects.get(email="Ana@example.com")
        assert "Created Ana@example.com (Owner)" in out
        assert (user.first_name, user.last_name) == ("Ana", "Souza")
        assert user.role == Role.OWNER and user.email_verified
        assert user.is_staff and user.is_superuser
        assert user.check_password(PASSWORD)

    def test_weak_password_creates_nothing(self):
        with pytest.raises(CommandError):
            self._run(
                "--email", "a@example.com", "--full-name", "Ana", "--password-stdin",
                stdin="123\n",
            )  # fmt: skip
        assert not get_user_model().objects.exists()

    def test_interactive_asks_twice_and_shows_the_rules(self):
        answers = iter([PASSWORD, "different-pass-99", PASSWORD, PASSWORD])
        with mock.patch(
            "tripaulx.accounts.management.commands.create_workspace_admin.getpass",
            lambda _prompt: next(answers),
        ):
            out = self._run("--email", "b@example.com", "--full-name", "Bea Lima")
        assert "Password rules:" in out
        assert "do not match" in out
        assert get_user_model().objects.filter(email="b@example.com").exists()

    def test_duplicate_email_and_unknown_workspace_fail(self):
        self.make_user(email="c@example.com")
        with pytest.raises(CommandError):
            self._run(
                "--email", "c@example.com", "--full-name", "C", "--password-stdin"
            )
        with pytest.raises(CommandError):
            call_command(
                "create_workspace_admin", "--schema", "nope",
                "--email", "x@example.com", "--full-name", "X", "--password-stdin",
            )  # fmt: skip


class IfNoneTests(TenantTestCase):
    def test_if_none_skips_when_an_owner_exists(self):
        self.make_user(email="owner@example.com", role=Role.OWNER)
        out = StringIO()
        call_command(
            "create_workspace_admin", "--schema", connection.schema_name,
            "--if-none", stdout=out,
        )  # fmt: skip
        assert "already has an owner" in out.getvalue()
        assert get_user_model().objects.count() == 1
