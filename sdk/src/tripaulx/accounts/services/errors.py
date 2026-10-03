"""Exceptions raised by account services.

Every error carries a user-facing (translated) message, an HTTP status the
API answers with, and optional extra fields for the response body. Views
never catch them one by one: the base API view turns any
:class:`AccountsError` into a response.
"""

from __future__ import annotations

from typing import Any


class AccountsError(Exception):
    """Base class: a failed account operation with a message for the user."""

    status_code = 400

    def __init__(self, message: Any, **extra: Any) -> None:
        """Store the message and extra response fields."""
        super().__init__(str(message))
        self.message = str(message)
        self.extra = extra


class NotFound(AccountsError):
    """The object does not exist (or belongs to someone else)."""

    status_code = 404


class CodeError(AccountsError):
    """An e-mail code is missing, expired, exhausted or wrong."""


class RecoveryCodeError(AccountsError):
    """A recovery code is invalid or was already used."""


class TotpError(AccountsError):
    """The authenticator-app flow failed."""


class PasskeyError(AccountsError):
    """The passkey flow failed or a passkey rule was broken."""


class PasswordError(AccountsError):
    """A password reset or change failed."""


class LoginError(AccountsError):
    """Login refused (bad credentials, expired ticket...)."""


class InvalidCredentials(LoginError):
    """Wrong e-mail or password."""

    status_code = 401


class LoginForbidden(LoginError):
    """Correct password, but this way in is closed (passkey-only, unverified)."""

    status_code = 403


class MembershipError(AccountsError):
    """A member or invitation rule was broken."""


class MembershipForbidden(MembershipError):
    """The actor lacks the role needed for this change."""

    status_code = 403


class SignupError(AccountsError):
    """Workspace signup failed validation."""
