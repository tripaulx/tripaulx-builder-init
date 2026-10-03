"""Uploads: validate first, then send (encrypted when a master key is set).

Every check happens HERE, not only in views, so no code path can put in the
bucket something that was not vetted, and all of it runs before the first byte
leaves for the cloud.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from django.utils.translation import gettext as _

from .. import client, crypto
from ..conf import app_settings
from ..exceptions import StorageError
from . import policy
from .keys import ensure_tenant_key
from .streams import EncryptingStream


@dataclass(frozen=True)
class StoredFile:
    """What was stored in the bucket by an upload."""

    key: str
    name: str
    size: int
    content_type: str
    #: Whether the object is encrypted at rest. Encrypted objects have no
    #: direct link: they are served through :func:`download`.
    encrypted: bool = False


def upload(
    file: Any,
    key: str,
    content_type: str = "",
    *,
    types: Iterable[str] | None = None,
    max_bytes: int | None = None,
) -> StoredFile:
    """Upload a file-like (e.g. Django's ``UploadedFile``) under ``key``.

    ``types`` narrows ``ALLOWED_TYPES`` for this call (it can never widen it);
    ``max_bytes`` defaults to ``MAX_UPLOAD_BYTES``. Raises
    :class:`StorageError` for an empty or oversized file, a type outside the
    policy, or content whose magic bytes do not match the declared type.
    """
    ensure_tenant_key(key)
    size = policy.measure(file, max_bytes or app_settings.MAX_UPLOAD_BYTES)

    allowed = set(app_settings.ALLOWED_TYPES)
    accepted = allowed if types is None else allowed.intersection(types)
    kind = policy.declared_type(file, key, content_type)
    policy.check_type(kind, accepted)
    policy.check_signature(file, kind)
    if kind.startswith("image/"):
        policy.check_image_pixels(file)

    return _put(file, key, kind, size)


def upload_image(file: Any, key: str, content_type: str = "") -> StoredFile:
    """Upload an IMAGE: only ``image/*`` policy types, ``MAX_IMAGE_BYTES``.

    A separate door with a smaller limit, for logos, avatars and the like.
    """
    images = [kind for kind in app_settings.ALLOWED_TYPES if kind.startswith("image/")]
    return upload(
        file,
        key,
        content_type,
        types=images,
        max_bytes=app_settings.MAX_IMAGE_BYTES,
    )


def _put(file: Any, key: str, content_type: str, size: int) -> StoredFile:
    """Send an ALREADY VALIDATED file, encrypting it when a master key is set.

    With encryption on, the object's ``ContentType`` is ``octet-stream`` on
    purpose: what is stored is ciphertext. Keep the real type in your own
    database and pass it back when serving the file.
    """
    # Back to byte zero: the checks above peeked at the start of the file.
    file.seek(0)
    encrypted = crypto.encryption_enabled()
    body = EncryptingStream(file) if encrypted else file
    stored_type = "application/octet-stream" if encrypted else content_type

    try:
        client.get_client().upload_fileobj(
            body,
            app_settings.S3_BUCKET,
            key,
            ExtraArgs={"ContentType": stored_type},
        )
    except StorageError:
        raise
    except Exception as exc:  # boto3 raises a whole family of errors
        raise StorageError(
            _("Failed to upload the file: %(error)s") % {"error": exc}
        ) from exc

    return StoredFile(
        key=key,
        name=PurePosixPath(key).name,
        size=size,  # size of the ORIGINAL, which is what users see
        content_type=content_type,
        encrypted=encrypted,
    )
