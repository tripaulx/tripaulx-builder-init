"""Registration: a person creates their own account in the current schema.

Unlike signup (which creates a workspace and its owner), registration adds a
plain member to the workspace being visited, without an invitation. It is
meant for consumer products and is off by default (``REGISTRATION_ENABLED``).

Steps: validate the person, the profile and its extra fields, create the user
and send the verification code. With ``EMAIL_VERIFICATION_REQUIRED`` off, the
user starts verified and no code is sent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

from ..conf import app_settings
from ..models import EmailCodePurpose, Role
from ..signals import user_registered
from . import email_codes, identity, profiles, verification
from .errors import SignupError


@dataclass(frozen=True)
class RegistrationResult:
    """What registration created."""

    user: Any
    profile: str
    email_verification_required: bool
    extra: dict[str, Any] = field(default_factory=dict)


def enabled() -> bool:
    """Whether people may register by themselves."""
    return bool(app_settings.REGISTRATION_ENABLED)


def _taken() -> SignupError:
    """Error for an e-mail that already has an account here."""
    return SignupError(_("This e-mail already has an account."), field="email")


def _refuse_existing(email: str) -> None:
    """Raise when ``email`` already has an account in this schema.

    A pending (unverified) account gets a fresh code and an answer that sends
    the person to the code screen, instead of a dead end.
    """
    existing = get_user_model().objects.filter(email__iexact=email).first()
    if existing is None:
        return
    pending = existing.is_active and not existing.email_verified
    if not (pending and verification.required()):
        raise _taken()
    if email_codes.can_resend(existing, EmailCodePurpose.EMAIL_VERIFY):
        email_codes.issue_code(existing, EmailCodePurpose.EMAIL_VERIFY)
    raise SignupError(
        _("This e-mail is waiting for confirmation. Enter the code we sent."),
        field="email",
        email_verification_required=True,
        email=existing.email,
    )


def register(
    *,
    email: str,
    full_name: str,
    password: str,
    password_confirm: str,
    profile: str = "",
    extra: Mapping[str, Any] | None = None,
) -> RegistrationResult:
    """Create a member in the current schema; send the verification code if due.

    Raises:
        SignupError: invalid input, unknown profile or e-mail already used.
    """
    person = identity.clean_person(email, full_name, password, password_confirm)
    profile = profiles.clean_profile(profile)
    values = profiles.clean_extra(profile, extra or {})
    _refuse_existing(person.email)
    must_verify = verification.required()
    try:
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                email=person.email,
                password=password,
                first_name=person.first_name,
                last_name=person.last_name,
                role=Role.MEMBER,
                email_verified=not must_verify,
                **values,
            )
    except IntegrityError as exc:
        raise _taken() from exc
    if must_verify:
        email_codes.issue_code(user, EmailCodePurpose.EMAIL_VERIFY)
    user_registered.send(sender=type(user), user=user, profile=profile, extra=values)
    return RegistrationResult(user, profile, must_verify, values)
