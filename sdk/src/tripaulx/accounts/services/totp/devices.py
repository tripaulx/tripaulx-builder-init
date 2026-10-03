"""Lifecycle of a user's authenticator app.

1. :func:`begin_setup` creates a *pending* device with a new secret.
2. :func:`confirm_setup` accepts the first code (proof the app read the QR);
   only then does the app become the login's second factor.
3. :func:`verify_login` checks a login code, with anti-replay.
4. :func:`disable` requires a valid app or recovery code: a stolen session
   cannot turn the second factor off with one click.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from tripaulx.core import crypto
from tripaulx.core.conf import app_settings as core_settings

from ...conf import app_settings
from ...models import TotpDevice
from .. import recovery_codes
from ..errors import RecoveryCodeError, TotpError
from .algorithm import generate_secret, matching_step


def issuer() -> str:
    """Return the name shown by the authenticator app next to the account."""
    return app_settings.TOTP_ISSUER or core_settings.APP_NAME


def is_enabled(user: Any) -> bool:
    """Whether the user has a *confirmed* device (pending ones do not count)."""
    return TotpDevice.objects.filter(user=user, confirmed_at__isnull=False).exists()


def confirmed_device(user: Any) -> TotpDevice | None:
    """Return the confirmed device of ``user``, if any."""
    return TotpDevice.objects.filter(user=user, confirmed_at__isnull=False).first()


def begin_setup(user: Any) -> TotpDevice:
    """Create (or recreate) the pending device with a new secret.

    Refused while a confirmed device exists: switching phones means disabling
    first (with a code), or any open session could replace the second factor.
    """
    with transaction.atomic():
        device = TotpDevice.objects.select_for_update().filter(user=user).first()
        if device is not None and device.confirmed:
            raise TotpError(
                _("The authenticator app is already active. Disable it first.")
            )
        secret = crypto.encrypt(generate_secret())
        if device is None:
            return TotpDevice.objects.create(user=user, secret_encrypted=secret)
        device.secret_encrypted = secret
        device.last_step = 0
        device.save(update_fields=["secret_encrypted", "last_step", "updated_at"])
        return device


def confirm_setup(user: Any, code: str) -> TotpDevice:
    """Confirm the pending device with the app's first code."""
    with transaction.atomic():
        device = TotpDevice.objects.select_for_update().filter(user=user).first()
        if device is None or device.confirmed:
            raise TotpError(_("There is no pending setup. Start again."))
        step = matching_step(device.secret, code)
        if step is None:
            raise TotpError(
                _("Invalid code. Check the time on your phone and try again.")
            )
        now = timezone.now()
        device.confirmed_at = device.last_used_at = now
        device.last_step = step
        device.save(
            update_fields=["confirmed_at", "last_used_at", "last_step", "updated_at"]
        )
        return device


def verify_login(user: Any, code: str) -> TotpDevice:
    """Check a login code, refusing a code that was already accepted."""
    with transaction.atomic():
        device = (
            TotpDevice.objects.select_for_update()
            .filter(user=user, confirmed_at__isnull=False)
            .first()
        )
        if device is None:
            raise TotpError(_("This account has no active authenticator app."))
        step = matching_step(device.secret, code)
        if step is None:
            raise TotpError(_("Invalid authenticator code."))
        if step <= device.last_step:
            raise TotpError(_("This code was already used. Wait for the next one."))
        device.last_step = step
        device.last_used_at = timezone.now()
        device.save(update_fields=["last_step", "last_used_at", "updated_at"])
        return device


def disable(user: Any, code: str) -> None:
    """Remove the device; requires an app code or a recovery code."""
    if not is_enabled(user):
        raise TotpError(_("The authenticator app is not active."))
    if recovery_codes.looks_like_recovery_code(code):
        try:
            recovery_codes.verify_code(user, code)
        except RecoveryCodeError as exc:
            raise TotpError(exc.message) from exc
    else:
        verify_login(user, code)
    TotpDevice.objects.filter(user=user).delete()


def cancel_setup(user: Any) -> None:
    """Drop a pending device (the user left the setup screen)."""
    TotpDevice.objects.filter(user=user, confirmed_at__isnull=True).delete()
