"""E-mails sent by the accounts app (templates under ``tripaulx/mail/``)."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from tripaulx.core.conf import app_settings as core_settings
from tripaulx.mail.services import send_templated_mail

from ..conf import app_settings
from ..models import EmailCodePurpose


def _subject(purpose: str) -> str:
    """Return the translated subject of an e-mail, prefixed with the brand."""
    subjects = {
        EmailCodePurpose.EMAIL_VERIFY: _("Confirm your e-mail"),
        EmailCodePurpose.LOGIN_2FA: _("Your access code"),
        EmailCodePurpose.PASSWORD_RESET: _("Reset your password"),
        EmailCodePurpose.INVITE: _("You have been invited"),
    }
    return f"{core_settings.APP_NAME} · {subjects[purpose]}"


def send_code(user: Any, purpose: str, code: str) -> None:
    """E-mail ``code`` to ``user``; the template is named after the purpose."""
    send_templated_mail(
        str(purpose),
        subject=_subject(purpose),
        to=[user.email],
        context={
            "user": user,
            "first_name": (getattr(user, "first_name", "") or "").strip(),
            "code": code,
            "code_spaced": " ".join(code),
            "minutes": app_settings.OTP_TTL_SECONDS // 60,
        },
    )


def send_invitation(
    email: str, *, url: str, inviter: Any, workspace: str, days: int
) -> None:
    """E-mail an invitation link."""
    send_templated_mail(
        str(EmailCodePurpose.INVITE),
        subject=_subject(EmailCodePurpose.INVITE),
        to=[email],
        context={
            "url": url,
            "inviter": getattr(inviter, "email", ""),
            "workspace": workspace,
            "days": days,
        },
    )
