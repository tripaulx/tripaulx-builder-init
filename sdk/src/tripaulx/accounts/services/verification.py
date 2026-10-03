"""E-mail address verification by code."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from ..models import EmailCodePurpose
from . import email_codes
from .errors import CodeError


def verify_email(email: str, code: str) -> Any:
    """Check the verification code of ``email`` and mark it verified.

    An unknown e-mail gets the same error as a wrong code.
    """
    user = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        raise CodeError(_("Invalid code."))
    email_codes.verify_code(user, EmailCodePurpose.EMAIL_VERIFY, code)
    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=["email_verified"])
    return user


def resend_verification(email: str) -> None:
    """Send a new code to a pending (unverified) account; always silent."""
    user = (
        get_user_model()
        .objects.filter(email__iexact=email, is_active=True, email_verified=False)
        .first()
    )
    if user is not None and email_codes.can_resend(user, EmailCodePurpose.EMAIL_VERIFY):
        email_codes.issue_code(user, EmailCodePurpose.EMAIL_VERIFY)
