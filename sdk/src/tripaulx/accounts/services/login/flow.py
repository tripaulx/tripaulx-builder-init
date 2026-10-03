"""Login orchestrator: password, second factor, trusted device and passkey.

Every login ends with a second factor; the only shortcuts are a valid
trusted-device token and a passkey (which is itself a strong factor). The
functions return a :class:`LoginOutcome`; refusals raise the errors of
:mod:`tripaulx.accounts.services.errors`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.http import HttpRequest
from django.utils.translation import gettext as _

from ...models import EmailCodePurpose
from ...signals import user_logged_in_2fa
from .. import email_codes, passkeys, recovery_codes, tokens, trusted_devices
from ..errors import InvalidCredentials, LoginError, LoginForbidden
from . import second_factor
from .tickets import make_ticket, read_ticket


@dataclass
class LoginOutcome:
    """Either a completed login (``user`` + ``tokens``) or a ``challenge``."""

    user: Any = None
    tokens: dict[str, str] | None = None
    challenge: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def complete_login(user: Any, request: HttpRequest, method: str, **extra: Any) -> Any:
    """Issue the tokens and announce the login."""
    update_last_login(None, user)
    user_logged_in_2fa.send(
        sender=type(user), user=user, request=request, method=method
    )
    return LoginOutcome(user=user, tokens=tokens.tokens_for(user), extra=extra)


def _require_verified_email(user: Any) -> None:
    """Refuse (and send a verification code) while the e-mail is unconfirmed."""
    if user.email_verified:
        return
    if email_codes.can_resend(user, EmailCodePurpose.EMAIL_VERIFY):
        email_codes.issue_code(user, EmailCodePurpose.EMAIL_VERIFY)
    raise LoginForbidden(
        _("Confirm your e-mail address with the code we sent you."),
        email_verification_required=True,
        email=user.email,
    )


def password_login(
    request: HttpRequest, email: str, password: str, device_token: str = ""
) -> LoginOutcome:
    """First step: check the password, then trusted device or second factor."""
    candidate = get_user_model().objects.filter(email__iexact=email).first()
    username = candidate.email if candidate is not None else email
    user = authenticate(request, username=username, password=password)
    if user is None:
        raise InvalidCredentials(_("Incorrect e-mail or password."))
    if passkeys.password_login_blocked(user):
        # Checked *after* the password on purpose: otherwise anyone could
        # find passkey-only accounts by typing an e-mail.
        raise LoginForbidden(
            _("This account signs in with a passkey only."), passkey_required=True
        )
    _require_verified_email(user)
    device = trusted_devices.find_valid_device(user, device_token)
    if device is not None:
        trusted_devices.touch(device)
        return complete_login(user, request, "trusted_device")
    found = second_factor.challenge(user)
    return LoginOutcome(
        challenge={"mfa_required": True, "ticket": make_ticket(user), **found}
    )


def verify_second_factor(
    request: HttpRequest,
    ticket: str,
    code: str,
    *,
    trust_device: bool = False,
    device_label: str = "",
) -> LoginOutcome:
    """Second step: check the code of the ticket's user and issue tokens."""
    user = read_ticket(ticket)
    if user is None:
        raise LoginError(_("Your session expired. Log in again."))
    method = second_factor.verify(user, code)
    extra: dict[str, Any] = {}
    if method == second_factor.METHOD_RECOVERY:
        extra["recovery_code_used"] = True
        extra["recovery_codes_remaining"] = recovery_codes.remaining(user)
    if trust_device:
        token = trusted_devices.issue_token(user, request, device_label)
        if token is not None:
            extra["device_token"] = token
            extra["device_token_max_age"] = trusted_devices.max_age()
    return complete_login(user, request, method, **extra)


def resend_code(ticket: str) -> None:
    """Send a new e-mail code for the ticket's user; always silent."""
    user = read_ticket(ticket)
    if user is not None:
        second_factor.resend(user)


def passkey_begin(request: HttpRequest, email: str = "") -> tuple[str, dict]:
    """Start a passkey login; without an e-mail any passkey may answer."""
    model = get_user_model()
    user = model.objects.filter(email__iexact=email).first() if email else None
    return passkeys.authentication_options(user, request=request)


def passkey_login(request: HttpRequest, ticket: str, credential: str) -> Any:
    """Finish a passkey login; the e-mail must be verified here too."""
    stored = passkeys.verify_authentication(ticket, credential, request=request)
    user = stored.user
    if not user.is_active:
        raise InvalidCredentials(_("This account is inactive."))
    _require_verified_email(user)
    return complete_login(user, request, "passkey")
