"""Signed, short-lived ticket linking the password step to the second factor.

The ticket carries the schema next to the user id: ids repeat across
workspaces, so a ticket from one workspace must never resolve a user in
another one.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core import signing
from django.db import connection

from ...conf import app_settings

SALT = "tripaulx.accounts.login_2fa"


def make_ticket(user: Any) -> str:
    """Return a ticket for ``user`` in the current schema."""
    return signing.TimestampSigner(salt=SALT).sign(
        f"{connection.schema_name}:{user.pk}"
    )


def read_ticket(ticket: str) -> Any:
    """Return the active user of a valid, unexpired ticket, or ``None``."""
    try:
        value = signing.TimestampSigner(salt=SALT).unsign(
            ticket or "", max_age=app_settings.LOGIN_TICKET_TTL_SECONDS
        )
    except signing.BadSignature:
        return None
    schema, _sep, pk = value.rpartition(":")
    if schema != connection.schema_name:
        return None
    return get_user_model().objects.filter(pk=pk, is_active=True).first()
