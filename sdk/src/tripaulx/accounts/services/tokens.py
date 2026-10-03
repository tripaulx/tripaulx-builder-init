"""JWTs (SimpleJWT) bound to the workspace schema that issued them.

One ``SECRET_KEY`` signs the tokens of the whole deploy, and ``user_id`` is
the sequential primary key of the users table **of each schema**: id 1 exists
in every workspace. Without anything else in the payload, a token issued by
``a.example.com`` would authenticate as a different person on
``b.example.com``. The defence is a ``schema`` claim stamped at issue time and
checked on every use. A token without the claim is refused too: its absence
never counts as permission.
"""

from __future__ import annotations

from typing import Any

from django.db import connection
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken, Token

#: Claim holding the schema the token was issued in. SimpleJWT copies refresh
#: claims into the access token, so stamping the refresh covers the pair.
CLAIM_SCHEMA = "schema"

#: Deliberately vague: a token from another workspace gets no confirmation
#: that it is valid somewhere else.
WRONG_SCHEMA = _("Token not valid for this workspace. Log in again.")


def check_schema(token: Token) -> None:
    """Refuse a token whose schema claim is not the current schema."""
    if token.get(CLAIM_SCHEMA) != connection.schema_name:
        raise InvalidToken({"detail": str(WRONG_SCHEMA)})


class TenantRefreshToken(RefreshToken):
    """Refresh token that refuses to be *read* outside its own schema.

    The check lives in ``__init__`` because a refresh token enters through
    paths that skip authentication (refresh and logout). Creating a new token
    (``token=None``) has nothing to check; :func:`refresh_for` stamps it.
    """

    def __init__(self, token: Any = None, verify: bool = True) -> None:
        """Decode the token and check its schema claim."""
        super().__init__(token, verify=verify)
        if token is not None and verify:
            check_schema(self)


def refresh_for(user: Any) -> RefreshToken:
    """Return a refresh token for ``user`` stamped with the current schema."""
    refresh = TenantRefreshToken.for_user(user)
    refresh[CLAIM_SCHEMA] = connection.schema_name
    return refresh


def tokens_for(user: Any) -> dict[str, str]:
    """Return the ``access``/``refresh`` pair, both bound to this schema."""
    refresh = refresh_for(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def blacklist_all(user: Any) -> int:
    """Blacklist every outstanding refresh token of ``user`` (end sessions)."""
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )

    count = 0
    for token in OutstandingToken.objects.filter(user=user):
        _obj, created = BlacklistedToken.objects.get_or_create(token=token)
        count += int(created)
    return count
