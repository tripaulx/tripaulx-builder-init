"""DRF authentication: SimpleJWT plus the workspace (schema) check.

Use it instead of the plain ``JWTAuthentication`` in
``DEFAULT_AUTHENTICATION_CLASSES`` (``tripaulx.settings.rest`` does). Why:
see :mod:`tripaulx.accounts.services.tokens`.
"""

from __future__ import annotations

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import Token

from ..services.tokens import check_schema


class TenantJWTAuthentication(JWTAuthentication):
    """Accept only tokens issued in the current workspace schema.

    The check runs in ``get_validated_token`` (not ``get_user``) so a foreign
    token dies before any query hits this schema.
    """

    def get_validated_token(self, raw_token: bytes) -> Token:
        """Validate the signature, then the schema claim."""
        token = super().get_validated_token(raw_token)
        check_schema(token)
        return token
