"""Names and password rules shared by signup, invitations and admin creation.

Django's password validators judge a password *against the person*
(``UserAttributeSimilarityValidator`` compares it with the e-mail and names),
so every place that sets a new password builds the would-be user first and
validates with it.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    password_validators_help_texts,
    validate_password,
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from .errors import PasswordError

NAME_MAX = 150


def split_full_name(full_name: str) -> tuple[str, str]:
    """Split ``"Ana Maria Souza"`` into ``("Ana", "Maria Souza")``.

    Extra spaces are collapsed; each part is cut to the model's 150 chars.
    """
    parts = " ".join((full_name or "").split()).split(" ", 1)
    first = parts[0] if parts and parts[0] else ""
    last = parts[1] if len(parts) > 1 else ""
    return first[:NAME_MAX], last[:NAME_MAX]


def candidate_user(email: str, first_name: str = "", last_name: str = "") -> Any:
    """Return an unsaved user carrying the attributes the validators compare."""
    return get_user_model()(email=email, first_name=first_name, last_name=last_name)


def password_rules() -> list[str]:
    """Return the active password rules, translated (for forms and prompts)."""
    return [str(text) for text in password_validators_help_texts()]


def check_new_password(password: str, confirmation: str, user: Any = None) -> None:
    """Require matching confirmation, then every configured password validator.

    Raises:
        PasswordError: with ``field`` set to the input that must be fixed.
    """
    if password != confirmation:
        raise PasswordError(
            _("The two passwords do not match."), field="password_confirm"
        )
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise PasswordError(" ".join(exc.messages), field="password") from exc
