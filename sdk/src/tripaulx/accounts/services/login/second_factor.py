"""The second factor: by app or by e-mail, required as ``MFA_POLICY`` says.

- ``always`` (default) asks everyone; ``privileged`` asks staff, owners and
  admins; ``optional`` asks nobody. Whatever the policy, a user who turned an
  authenticator app on is always asked.
- With a confirmed authenticator app, the 6-digit code is the app's and no
  e-mail is sent.
- Otherwise a code is e-mailed.
- A recovery code is accepted in the same field in both cases.
"""

from __future__ import annotations

from typing import Any

from ...conf import app_settings
from ...models import EmailCodePurpose
from .. import email_codes, recovery_codes, totp

METHOD_TOTP = "totp"
METHOD_EMAIL = "email"
METHOD_RECOVERY = "recovery_code"
#: Login that ended at the password because no second factor was due.
METHOD_PASSWORD = "password"

POLICY_ALWAYS = "always"
POLICY_PRIVILEGED = "privileged"
POLICY_OPTIONAL = "optional"


def mask_email(email: str) -> str:
    """Return ``j***e@example.com`` for ``jane@example.com``."""
    name, _sep, domain = email.partition("@")
    head = name[:1]
    tail = name[-1] if len(name) > 1 else ""
    return f"{head}***{tail}@{domain}"


def is_privileged(user: Any) -> bool:
    """Whether ``user`` is staff or manages the workspace (owner or admin)."""
    return bool(user.is_staff or getattr(user, "is_workspace_admin", False))


def needs_strong_factor(user: Any) -> bool:
    """Privileged account (staff, owner, admin) without an app or a passkey.

    Their login already requires a second factor, but the e-mail code is the
    weak one; clients use this flag to ask for an app or a passkey.
    """
    if not is_privileged(user):
        return False
    return not (totp.is_enabled(user) or user.passkeys.exists())


def is_required(user: Any) -> bool:
    """Whether the login of ``user`` must end with a second factor.

    An unknown policy value counts as ``always``: a typo never opens a door.
    """
    if totp.is_enabled(user):
        return True
    policy = app_settings.MFA_POLICY
    if policy == POLICY_OPTIONAL:
        return False
    if policy == POLICY_PRIVILEGED:
        return is_privileged(user)
    return True


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
