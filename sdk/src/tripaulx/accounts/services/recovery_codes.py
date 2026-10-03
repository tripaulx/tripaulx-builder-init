"""Recovery codes: the second factor that does not depend on e-mail or phone.

Format ``XXXXX-XXXXX`` over an alphabet without look-alike characters (no
O/0, I/1, S/5), so a code can be copied from paper without mistakes. Only the
hash is stored. Generating a new list always burns the previous one.
"""

from __future__ import annotations

import secrets
from typing import Any

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django.utils.translation import gettext as _

from ..conf import app_settings
from ..models import RecoveryCode
from .errors import RecoveryCodeError

ALPHABET = "ABCDEFGHJKLMNPQRTUVWXYZ2346789"
GROUP = 5
GROUPS = 2


def _random_code() -> str:
    """Return a code shaped ``XXXXX-XXXXX`` (about 49 bits of entropy)."""
    groups = [
        "".join(secrets.choice(ALPHABET) for _ in range(GROUP)) for _ in range(GROUPS)
    ]
    return "-".join(groups)


def normalize(code: str) -> str:
    """Upper-case and drop spaces, dashes and anything outside the alphabet."""
    return "".join(ch for ch in (code or "").upper() if ch in ALPHABET)


def looks_like_recovery_code(code: str) -> bool:
    """Tell a recovery code from a 6-digit code typed in the same field."""
    return len(normalize(code)) == GROUP * GROUPS


def generate_codes(user: Any, quantity: int | None = None, label: str = "") -> list:
    """Create ``quantity`` codes, invalidating the user's previous ones.

    Returns the codes in plain text: the only time they exist outside a hash.
    """
    quantity = quantity or app_settings.RECOVERY_CODES_QUANTITY
    if quantity < 1:
        raise ValueError("quantity must be at least 1")
    RecoveryCode.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now()
    )
    codes = [_random_code() for _ in range(quantity)]
    RecoveryCode.objects.bulk_create(
        [
            RecoveryCode(
                user=user,
                code_hash=make_password(normalize(code)),
                prefix=normalize(code)[:4],
                label=label,
            )
            for code in codes
        ]
    )
    return codes


def remaining(user: Any) -> int:
    """How many unused codes the user still has."""
    return RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()


def verify_code(user: Any, code: str) -> RecoveryCode:
    """Check and consume a recovery code; raise :class:`RecoveryCodeError`.

    Consumption is a conditional ``UPDATE``: two concurrent requests with the
    same code have a single winner.
    """
    normalized = normalize(code)
    if normalized:
        # Few codes per user and hashed values: compare against each one.
        for obj in RecoveryCode.objects.filter(user=user, used_at__isnull=True):
            if not check_password(normalized, obj.code_hash):
                continue
            now = timezone.now()
            claimed = RecoveryCode.objects.filter(
                pk=obj.pk, used_at__isnull=True
            ).update(used_at=now)
            if not claimed:
                break
            obj.used_at = now
            return obj
    raise RecoveryCodeError(_("Invalid or already used recovery code."))
