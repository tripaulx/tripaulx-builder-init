"""Trusted-device tokens ("trust this device" skips the second factor).

The raw token is returned to the client once; only its sha256 is stored.
"""

from __future__ import annotations

from datetime import timedelta
import secrets
from typing import Any

from django.db import DatabaseError, transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone

from ..conf import app_settings
from ..models import TrustedDevice


def client_ip(request: HttpRequest | None) -> str | None:
    """Return the client IP, preferring the first ``X-Forwarded-For`` entry."""
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def max_age() -> int:
    """Lifetime of a trusted-device token, in seconds."""
    return int(app_settings.TRUSTED_DEVICE_MAX_AGE)


def issue_token(
    user: Any, request: HttpRequest | None = None, label: str = ""
) -> str | None:
    """Trust the current device and return its raw token.

    Fail-safe: on a database error it returns ``None`` and the login goes on
    (the user only misses the shortcut).
    """
    token = secrets.token_urlsafe(32)
    agent = request.META.get("HTTP_USER_AGENT", "") if request is not None else ""
    try:
        with transaction.atomic():
            TrustedDevice.objects.create(
                user=user,
                token_hash=TrustedDevice.hash_token(token),
                device_label=(label or "")[:120],
                ip_address=client_ip(request),
                user_agent=agent or "",
                expires_at=timezone.now() + timedelta(seconds=max_age()),
            )
    except DatabaseError:
        return None
    return token


def find_valid_device(user: Any, token: str) -> TrustedDevice | None:
    """Return the valid device of ``user`` for ``token``, or ``None``."""
    if not token:
        return None
    device = TrustedDevice.objects.filter(
        token_hash=TrustedDevice.hash_token(token), user=user, is_active=True
    ).first()
    if device is None or not device.is_valid:
        return None
    return device


def touch(device: TrustedDevice) -> None:
    """Record that the device was just used."""
    device.last_used_at = timezone.now()
    device.save(update_fields=["last_used_at", "updated_at"])


def active_devices(user: Any) -> QuerySet[TrustedDevice]:
    """Return the user's active, unexpired devices, newest first."""
    return TrustedDevice.objects.filter(
        user=user, is_active=True, expires_at__gt=timezone.now()
    )


def revoke_device(user: Any, pk: Any) -> bool:
    """Revoke one of the user's devices; return whether one was revoked."""
    return bool(
        TrustedDevice.objects.filter(user=user, pk=pk, is_active=True).update(
            is_active=False, updated_at=timezone.now()
        )
    )


def revoke_devices(user: Any) -> int:
    """Revoke every trusted device of the user; return how many."""
    return TrustedDevice.objects.filter(user=user, is_active=True).update(
        is_active=False, updated_at=timezone.now()
    )
