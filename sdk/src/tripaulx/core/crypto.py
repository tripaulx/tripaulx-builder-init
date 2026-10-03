"""Symmetric encryption of sensitive fields (API keys, TOTP secrets).

Values are encrypted with Fernet (AES-128-CBC + HMAC-SHA256). The key comes
from ``TRIPAULX["FIELD_ENCRYPTION_KEY"]``; when it is empty, a key is derived
from ``SECRET_KEY`` (sha256, urlsafe base64). Deriving from ``SECRET_KEY`` means
that rotating it makes every stored token unreadable, so production must set
an explicit key: the template's ``prod.py`` calls :func:`validate_field_key`.
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .conf import app_settings

logger = logging.getLogger("tripaulx.crypto")


def generate_key() -> str:
    """Return a new random Fernet key, ready for ``FIELD_ENCRYPTION_KEY``."""
    return Fernet.generate_key().decode()


def validate_field_key(key: str | bytes | None) -> None:
    """Raise ``ImproperlyConfigured`` unless ``key`` is a usable Fernet key."""
    if not key:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY is not set. Generate one with: python -c "
            '"from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    try:
        Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY must be 32 url-safe base64-encoded bytes."
        ) from exc


def _fernet() -> Fernet:
    """Build the cipher from the configured key, or one derived from SECRET_KEY."""
    key = app_settings.FIELD_ENCRYPTION_KEY or ""
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    """Encrypt ``value`` and return the token; an empty value stays empty."""
    if not value:
        return ""
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt ``token``; an empty or unreadable token returns ``""``.

    A non-empty token that fails (wrong, missing or rotated key) is logged at
    ERROR level, so a key change never silently turns a secret into "not
    configured".
    """
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        logger.error(
            "Could not decrypt a stored secret: FIELD_ENCRYPTION_KEY is wrong, "
            "missing or was rotated without re-encrypting. Treating the value "
            "as not configured."
        )
        return ""
