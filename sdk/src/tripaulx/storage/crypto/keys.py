"""The master key that wraps every file key (``FILE_ENCRYPTION_KEY``)."""

from __future__ import annotations

import base64
import binascii
import os
from typing import Any

from django.utils.translation import gettext as _

from ..conf import app_settings
from ..exceptions import StorageError, missing_dependency

KEY_SIZE = 32  # AES-256


def encryption_enabled() -> bool:
    """Return whether a master key is configured (otherwise files go in clear)."""
    return bool(app_settings.FILE_ENCRYPTION_KEY)


def master_key() -> bytes:
    """Return the decoded master key, or raise :class:`StorageError`."""
    raw = app_settings.FILE_ENCRYPTION_KEY
    if not raw:
        raise StorageError(
            _(
                "File encryption has no key: set FILE_ENCRYPTION_KEY (32 bytes "
                "in base64; generate one with `manage.py generate_file_key`)."
            )
        )
    try:
        key = base64.urlsafe_b64decode(raw)
    except (binascii.Error, ValueError) as exc:
        raise StorageError(_("FILE_ENCRYPTION_KEY is not valid base64.")) from exc
    if len(key) != KEY_SIZE:
        raise StorageError(
            _("FILE_ENCRYPTION_KEY must be 32 bytes long (it has %(size)d).")
            % {"size": len(key)}
        )
    return key


def generate_master_key() -> str:
    """Return a new random master key, base64-encoded for the environment."""
    return base64.urlsafe_b64encode(os.urandom(KEY_SIZE)).decode()


def aesgcm(key: bytes) -> Any:
    """Return an ``AESGCM`` cipher for ``key`` (``cryptography`` is optional)."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise missing_dependency("cryptography") from exc
    return AESGCM(key)
