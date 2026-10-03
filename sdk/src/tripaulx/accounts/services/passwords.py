"""Password reset by e-mail code and password change while logged in.

Both end every other session: trusted devices are revoked and every
outstanding refresh token is blacklisted, so a stolen token pair cannot keep
rotating after the password changed.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from ..models import EmailCodePurpose
from . import email_codes, tokens, trusted_devices
from .errors import CodeError, PasswordError


def _generic_code_error() -> PasswordError:
    """One message for every code failure, so accounts cannot be enumerated."""
    return PasswordError(_("Invalid or expired code. Request a new one."))


def _active_user(email: str) -> Any:
    """Return the active user with ``email`` in this schema, or ``None``."""
    model = get_user_model()
    return model.objects.filter(email__iexact=email, is_active=True).first()


def check_strength(password: str, user: Any = None) -> None:
    """Run the password validators; raise :class:`PasswordError`."""
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise PasswordError(" ".join(exc.messages)) from exc


def end_sessions(user: Any) -> None:
    """Revoke trusted devices and blacklist all refresh tokens of ``user``."""
    trusted_devices.revoke_devices(user)
    tokens.blacklist_all(user)


def issue_reset(email: str) -> None:
    """E-mail a reset code **if** an active user has ``email``.

    Always silent: it never reveals whether the account exists, and it
    respects the resend cooldown.
    """
    user = _active_user(email)
    if user is None:
        return
    if email_codes.can_resend(user, EmailCodePurpose.PASSWORD_RESET):
        email_codes.issue_code(user, EmailCodePurpose.PASSWORD_RESET)


def confirm_reset(email: str, code: str, new_password: str) -> Any:
    """Check the code, set the new password and end every session.

    The password is validated **before** the code is consumed, so a weak
    password never burns the single-use code.
    """
    user = _active_user(email)
    check_strength(new_password, user)
    if user is None:
        raise _generic_code_error()
    try:
        email_codes.verify_code(user, EmailCodePurpose.PASSWORD_RESET, code)
    except CodeError as exc:
        raise _generic_code_error() from exc
    user.set_password(new_password)
    user.save(update_fields=["password"])
    end_sessions(user)
    return user


def change_password(user: Any, current: str, new_password: str) -> None:
    """Change the password of a logged-in user who knows the current one."""
    if not user.check_password(current):
        raise PasswordError(_("The current password is incorrect."))
    check_strength(new_password, user)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    end_sessions(user)
