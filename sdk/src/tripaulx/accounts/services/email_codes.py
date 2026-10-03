"""Issue, send and check the e-mail codes (verification, 2FA, reset).

Codes are numeric, stored only as a hash, with expiry and an attempt limit.
Each new code consumes the previous active ones of the same purpose.
"""

from __future__ import annotations

from datetime import timedelta
import secrets
from typing import Any

from django.contrib.auth.hashers import check_password, make_password
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext as _

from ..conf import app_settings
from ..models import EmailCode
from . import notifications
from .errors import CodeError


def _random_code(length: int) -> str:
    """Return ``length`` random digits."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def can_resend(user: Any, purpose: str) -> bool:
    """Whether the resend cooldown of ``purpose`` has passed (anti-spam)."""
    last = EmailCode.objects.filter(user=user, purpose=purpose).first()
    if last is None:
        return True
    elapsed = (timezone.now() - last.created_at).total_seconds()
    return elapsed >= app_settings.OTP_RESEND_COOLDOWN


def issue_code(user: Any, purpose: str) -> EmailCode:
    """Create a code, consume the previous ones and e-mail it."""
    now = timezone.now()
    EmailCode.objects.filter(
        user=user, purpose=purpose, consumed_at__isnull=True
    ).update(consumed_at=now)
    code = _random_code(app_settings.OTP_LENGTH)
    obj = EmailCode.objects.create(
        user=user,
        purpose=purpose,
        code_hash=make_password(code),
        expires_at=now + timedelta(seconds=app_settings.OTP_TTL_SECONDS),
    )
    notifications.send_code(user, purpose, code)
    return obj


def verify_code(user: Any, purpose: str, code: str) -> EmailCode:
    """Check the active code and consume it; raise :class:`CodeError`.

    Writes are atomic (``F()`` and conditional ``UPDATE``): concurrent wrong
    guesses all count, and two concurrent requests with the same valid code
    have a single winner.
    """
    obj = EmailCode.objects.filter(
        user=user, purpose=purpose, consumed_at__isnull=True
    ).first()
    if obj is None:
        raise CodeError(_("No active code. Request a new one."))
    if obj.is_expired:
        raise CodeError(_("Code expired. Request a new one."))
    if obj.attempts >= app_settings.OTP_MAX_ATTEMPTS:
        EmailCode.objects.filter(pk=obj.pk, consumed_at__isnull=True).update(
            consumed_at=timezone.now()
        )
        raise CodeError(_("Too many attempts. Request a new code."))
    if not check_password(code, obj.code_hash):
        EmailCode.objects.filter(pk=obj.pk).update(attempts=F("attempts") + 1)
        raise CodeError(_("Invalid code."))
    now = timezone.now()
    claimed = EmailCode.objects.filter(pk=obj.pk, consumed_at__isnull=True).update(
        consumed_at=now
    )
    if not claimed:
        raise CodeError(_("Invalid code."))
    obj.consumed_at = now
    return obj
