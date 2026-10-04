"""Full-name splitting, password rules and the confirmation check."""

from django.test import override_settings
import pytest

from tripaulx.accounts.services import identity
from tripaulx.accounts.services.errors import PasswordError


@pytest.mark.parametrize(
    ("full_name", "expected"),
    [
        ("Ana Maria  Souza", ("Ana", "Maria Souza")),
        ("  Ana  ", ("Ana", "")),
        ("", ("", "")),
        ("x" * 200, ("x" * 150, "")),
    ],
)
def test_split_full_name(full_name, expected):
    assert identity.split_full_name(full_name) == expected


def test_mismatch_is_reported_on_the_confirmation_field():
    with pytest.raises(PasswordError) as exc:
        identity.check_new_password("one-strong-pass-1", "two-strong-pass-2")
    assert exc.value.extra == {"field": "password_confirm"}


def test_password_similar_to_the_person_is_rejected():
    user = identity.candidate_user("ana.souza@example.com", "Ana", "Souza")
    with pytest.raises(PasswordError) as exc:
        identity.check_new_password("ana.souza", "ana.souza", user)
    assert exc.value.extra == {"field": "password"}


def test_rules_follow_the_configured_validators():
    assert len(identity.password_rules()) == 4
    with override_settings(AUTH_PASSWORD_VALIDATORS=[]):
        assert identity.password_rules() == []
