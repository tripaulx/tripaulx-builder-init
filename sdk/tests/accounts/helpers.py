"""Shared helpers of the accounts tests."""

from __future__ import annotations

import re
from typing import Any

from django.core import mail

from tripaulx.accounts.models import WebAuthnCredential
from tripaulx.core.testing import TenantAPITestCase

CODE_RE = re.compile(r"\b(\d{6})\b")
PASSWORD = "correct-horse-battery-42"

LOGIN = "/api/auth/login/"
LOGIN_VERIFY = "/api/auth/login/verify/"
LOGIN_RESEND = "/api/auth/login/resend/"
ME = "/api/auth/me/"
REFRESH = "/api/auth/token/refresh/"


def code_from_mail(index: int = -1) -> str:
    """Return the 6-digit code of a sent e-mail (the last one by default)."""
    match = CODE_RE.search(mail.outbox[index].body)
    assert match is not None, "the e-mail should contain a 6-digit code"
    return match.group(1)


def make_passkey(user: Any, credential_id: str = "cred-1") -> WebAuthnCredential:
    """Store a fake passkey (enough for the rules; not for a ceremony)."""
    return WebAuthnCredential.objects.create(
        user=user, credential_id=credential_id, public_key="pk", name="Key"
    )


class AccountsTestCase(TenantAPITestCase):
    """Tenant API test case with a verified user and login helpers."""

    email = "jane@example.com"

    def verified_user(self, email: str | None = None, **extra: Any) -> Any:
        """Create a user with a confirmed e-mail and the shared password."""
        return self.make_user(
            email=email or self.email, password=PASSWORD, email_verified=True, **extra
        )

    def login(self, user: Any, password: str = PASSWORD, **data: Any) -> Any:
        """POST the first login step for ``user``."""
        body = {"email": user.email, "password": password, **data}
        return self.anon_api_client().post(LOGIN, body, format="json")

    def verify(self, ticket: str, code: str, **data: Any) -> Any:
        """POST the second login step."""
        body = {"ticket": ticket, "code": code, **data}
        return self.anon_api_client().post(LOGIN_VERIFY, body, format="json")
