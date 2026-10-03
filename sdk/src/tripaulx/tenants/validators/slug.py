"""Rules for workspace slugs (which are also schema names).

A slug starts with a letter and holds 3-30 lowercase letters, digits or
underscores. In the subdomain, ``_`` becomes ``-``.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from ..conf import app_settings

SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,29}$")

# Labels that would be confused with the platform or with infrastructure.
RESERVED_SLUGS: frozenset[str] = frozenset(
    {
        "admin", "api", "app", "apps", "assets", "auth", "beta", "billing",
        "blog", "cdn", "checkout", "connect", "demo", "dev", "docs", "email",
        "files", "ftp", "help", "hooks", "imap", "login", "mail", "media",
        "mx", "ns1", "ns2", "pay", "public", "root", "sandbox", "site",
        "sites", "smtp", "sso", "stage", "staging", "static", "status",
        "store", "support", "system", "template", "test", "webhook",
        "webhooks", "www",
    }
)  # fmt: skip


def reserved_slugs() -> frozenset[str]:
    """Return the built-in reserved slugs plus the project's extra ones."""
    return RESERVED_SLUGS | frozenset(app_settings.EXTRA_RESERVED_SLUGS)


def validate_workspace_slug(value: str) -> None:
    """Raise ``ValidationError`` when ``value`` cannot be a workspace slug."""
    if not SLUG_PATTERN.fullmatch(value or ""):
        raise ValidationError(
            _(
                "Use 3 to 30 lowercase letters, digits or underscores, "
                "starting with a letter."
            ),
            code="invalid_slug",
        )
    if value.startswith("pg_") or value in reserved_slugs():
        raise ValidationError(_("This address is reserved."), code="reserved_slug")
