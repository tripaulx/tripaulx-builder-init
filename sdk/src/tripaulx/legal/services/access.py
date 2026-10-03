"""Who may read the restricted (governance) documents.

The rule: an authenticated, active user with a verified e-mail, in an allowed
schema (``LEGAL_SCHEMAS``; empty means every workspace), who is either a
workspace admin or has an e-mail in ``LEGAL_ALLOWED_EMAIL_DOMAINS``.
Public documents need none of this.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.db import connection

from ..conf import app_settings


def email_domain_allowed(email: str, domains: Iterable[str]) -> bool:
    """Whether the domain of ``email`` is exactly one of ``domains``.

    Only exact matches count: ``x@example.com.attacker.test`` and
    ``x@sub.example.com`` are not ``example.com``.
    """
    _local, separator, domain = (email or "").strip().rpartition("@")
    if not separator or not _local:
        return False
    allowed = {item.strip().casefold() for item in domains if item.strip()}
    return domain.casefold() in allowed


def schema_allowed(schema_name: str | None = None) -> bool:
    """Whether restricted documents are served in ``schema_name``."""
    schema_name = schema_name or connection.schema_name
    schemas = tuple(app_settings.LEGAL_SCHEMAS)
    return not schemas or schema_name in schemas


def can_read_restricted(user: Any, schema_name: str | None = None) -> bool:
    """Apply the access rule of restricted documents to ``user``."""
    if not (
        user
        and user.is_authenticated
        and user.is_active
        and getattr(user, "email_verified", False)
        and schema_allowed(schema_name)
    ):
        return False
    if getattr(user, "is_workspace_admin", False):
        return True
    return email_domain_allowed(
        getattr(user, "email", ""), app_settings.LEGAL_ALLOWED_EMAIL_DOMAINS
    )
