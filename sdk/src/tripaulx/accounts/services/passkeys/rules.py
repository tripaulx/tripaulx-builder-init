"""Passkey-only login and the rules that keep an account reachable.

``password_login_disabled`` only takes effect while the user has at least one
passkey, and the last passkey cannot be removed while password login is off;
otherwise the account would have no way in at all.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from ...models import WebAuthnCredential
from ..errors import NotFound, PasskeyError


def password_login_blocked(user: Any) -> bool:
    """Whether e-mail + password login is closed for ``user``.

    Requires **both** the option and a passkey: if the passkeys disappear
    (e.g. removed by an admin), the password works again.
    """
    return bool(user.password_login_disabled) and user.passkeys.exists()


def set_password_login_disabled(user: Any, disabled: bool) -> None:
    """Turn password login off or on; turning it off requires a passkey."""
    if disabled and not user.passkeys.exists():
        raise PasskeyError(
            _("Register a passkey before turning off e-mail and password login.")
        )
    user.password_login_disabled = bool(disabled)
    user.save(update_fields=["password_login_disabled"])


def get_passkey(user: Any, pk: Any) -> WebAuthnCredential | None:
    """Return the passkey ``pk`` of ``user`` (never another user's)."""
    return user.passkeys.filter(pk=pk).first()


def delete_passkey(user: Any, pk: Any) -> None:
    """Remove a passkey, except the last one while password login is off.

    A missing passkey is not an error (idempotent): the result the user
    wanted, the passkey not existing, already holds.
    """
    target = get_passkey(user, pk)
    if target is None:
        return
    if user.password_login_disabled and user.passkeys.count() == 1:
        raise PasskeyError(
            _(
                "This is the account's only passkey and password login is off. "
                "Turn password login back on before removing it."
            )
        )
    target.delete(hard=True)


def rename_passkey(user: Any, pk: Any, name: str) -> WebAuthnCredential:
    """Rename one of the user's passkeys."""
    target = get_passkey(user, pk)
    if target is None:
        raise NotFound(_("Passkey not found."))
    name = (name or "").strip()
    if not name:
        raise PasskeyError(_("The name cannot be empty."))
    target.name = name[:120]
    target.save(update_fields=["name", "updated_at"])
    return target
