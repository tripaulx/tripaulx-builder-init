"""The second factor: always required, by app or by e-mail.

- With a confirmed authenticator app, the 6-digit code is the app's and no
  e-mail is sent.
- Otherwise a code is e-mailed.
- A recovery code is accepted in the same field in both cases.
"""

from __future__ import annotations

from typing import Any

from ...models import EmailCodePurpose
from .. import email_codes, recovery_codes, totp

METHOD_TOTP = "totp"
METHOD_EMAIL = "email"
METHOD_RECOVERY = "recovery_code"


def mask_email(email: str) -> str:
    """Return ``j***e@example.com`` for ``jane@example.com``."""
    name, _sep, domain = email.partition("@")
    head = name[:1]
    tail = name[-1] if len(name) > 1 else ""
    return f"{head}***{tail}@{domain}"


def needs_strong_factor(user: Any) -> bool:
    """Privileged account (staff, owner, admin) without an app or a passkey.

    Their login already requires a second factor, but the e-mail code is the
    weak one; clients use this flag to ask for an app or a passkey.
    """
    privileged = user.is_staff or getattr(user, "is_workspace_admin", False)
    if not privileged:
        return False
    return not (totp.is_enabled(user) or user.passkeys.exists())


def challenge(user: Any) -> dict[str, Any]:
    """Start the second factor; return what the client needs to ask for it."""
    if totp.is_enabled(user):
        return {"mfa_method": METHOD_TOTP}
    email_codes.issue_code(user, EmailCodePurpose.LOGIN_2FA)
    return {"mfa_method": METHOD_EMAIL, "masked_email": mask_email(user.email)}


def resend(user: Any) -> None:
    """Send a new e-mail code when allowed (never for app users)."""
    if totp.is_enabled(user):
        return
    if email_codes.can_resend(user, EmailCodePurpose.LOGIN_2FA):
        email_codes.issue_code(user, EmailCodePurpose.LOGIN_2FA)


def verify(user: Any, code: str) -> str:
    """Check ``code`` and return the method that matched; raise on failure."""
    if recovery_codes.looks_like_recovery_code(code):
        recovery_codes.verify_code(user, code)
        return METHOD_RECOVERY
    if totp.is_enabled(user):
        totp.verify_login(user, code)
        return METHOD_TOTP
    email_codes.verify_code(user, EmailCodePurpose.LOGIN_2FA, code)
    return METHOD_EMAIL
