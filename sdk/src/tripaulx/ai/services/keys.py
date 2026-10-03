"""Adding and deleting provider API keys, with who and when.

Every key change goes through here (API, admin, tests). It is the only place
that knows the rules the table cannot enforce alone:

1. At most one active key per provider. Adding one closes the previous key
   of the same provider (``replaced``) in the same transaction, under
   ``select_for_update``; the partial unique constraint backs it up.
2. Closing wipes the secret. The row stays for the audit trail; the token
   does not.
3. A key that would not fit in an HTTP header is refused on entry.

The actor is recorded twice: a foreign key and a frozen label (name or
e-mail). The foreign key goes away with the user; the label does not.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from tripaulx.ai import providers
from tripaulx.ai.models import AIKey, KeyClosedReason
from tripaulx.ai.providers.errors import key_complaint
from tripaulx.core import crypto


class InvalidKey(ValueError):
    """The key is not usable; the message says why."""


def actor_label(user: Any) -> str:
    """Name of whoever acted, frozen for the audit (empty without a user)."""
    if user is None or not getattr(user, "pk", None):
        return ""
    return (user.get_full_name() or user.email or "").strip()[:254]


def _actor(user: Any) -> Any:
    return user if getattr(user, "pk", None) else None


def active(provider: str) -> AIKey | None:
    """Return the key in use for ``provider``, or ``None``."""
    return AIKey.objects.active_for(provider)


def history(provider: str, limit: int = 10) -> list[AIKey]:
    """Return closed keys of ``provider``, most recent first (up to ``limit``)."""
    return list(
        AIKey.objects.filter(provider=provider, closed_at__isnull=False).order_by(
            "-closed_at", "-pk"
        )[:limit]
    )


def _close(keys: list[AIKey], *, by: Any, reason: str) -> None:
    """Close the (already locked) ``keys``, wiping their secrets."""
    now = timezone.now()
    for key in keys:
        key.closed_at = now
        key.closed_by = _actor(by)
        key.closed_by_label = actor_label(by)
        key.closed_reason = reason
        key.api_key_encrypted = ""
        key.save(
            update_fields=[
                "closed_at",
                "closed_by",
                "closed_by_label",
                "closed_reason",
                "api_key_encrypted",
            ]
        )


def validate(provider: str, value: str) -> str:
    """Return the cleaned key, or raise :class:`InvalidKey`."""
    if providers.get_provider(provider) is None:
        raise InvalidKey(_("Unknown provider: %(provider)s.") % {"provider": provider})
    value = (value or "").strip()
    if not value:
        raise InvalidKey(_("Enter the API key."))
    complaint = key_complaint(value)
    if complaint is not None:
        raise InvalidKey(complaint)
    return value


def add(provider: str, value: str, *, by: Any) -> AIKey:
    """Store ``value`` as the active key of ``provider``, closing the old one.

    ``by`` is whoever adds it (``request.user``); ``None`` is accepted for
    paths without a user (shell, migrations) and recorded as such.
    """
    value = validate(provider, value)
    with transaction.atomic():
        previous = list(
            AIKey.objects.active().filter(provider=provider).select_for_update()
        )
        _close(previous, by=by, reason=KeyClosedReason.REPLACED)
        return AIKey.objects.create(
            provider=provider,
            api_key_encrypted=crypto.encrypt(value),
            created_by=_actor(by),
            created_by_label=actor_label(by),
        )


def delete(provider: str, *, by: Any) -> AIKey | None:
    """Close the active key of ``provider``; ``None`` when there was none.

    No key is not an error: the user asked for no key, and there is none.
    """
    with transaction.atomic():
        current = list(
            AIKey.objects.active().filter(provider=provider).select_for_update()
        )
        if not current:
            return None
        _close(current, by=by, reason=KeyClosedReason.DELETED)
        return current[0]
