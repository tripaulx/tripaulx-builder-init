"""Upload policy: accepted types, magic bytes, size and image dimensions.

The declared ``content_type`` comes from the client and proves nothing (any
file can be renamed), so the content's own signature is checked before a
single byte goes to the bucket. The allowlist is ``ALLOWED_TYPES`` (see
:mod:`tripaulx.storage.conf`).
"""

from __future__ import annotations

from collections.abc import Iterable
import mimetypes
from typing import Any

from django.utils.translation import gettext as _

from ..conf import app_settings
from ..exceptions import StorageError, missing_dependency
from .keys import clean_name

#: How many leading bytes are searched for an ``offset=None`` signature.
SIGNATURE_WINDOW = 1024

#: Types a browser may OPEN in a tab rather than download. Deliberately
#: independent from ``ALLOWED_TYPES``, so narrowing uploads never breaks how
#: older files are served. Never add HTML or SVG: opening them inline on the
#: application's domain would be cross-site scripting with the user's session.
INLINE_TYPES = frozenset(
    {"application/pdf", "image/jpeg", "image/png", "image/webp", "text/plain"}
)


def content_disposition(name: str, content_type: str) -> str:
    """Return the ``Content-Disposition``: open inline or download."""
    mode = "inline" if content_type in INLINE_TYPES else "attachment"
    return f'{mode}; filename="{clean_name(name)}"'


def measure(file: Any, limit: int) -> int:
    """Return the size in bytes, refusing empty files and files over ``limit``.

    ``size`` only exists on Django's ``UploadedFile``; a ``BytesIO`` (commands,
    tests) falls back to ``seek``/``tell``.
    """
    size = getattr(file, "size", None)
    if size is None:
        file.seek(0, 2)
        size = file.tell()
    if size <= 0:
        raise StorageError(_("The file is empty."))
    if size > limit:
        raise StorageError(
            _("The file exceeds the %(limit)s limit.") % {"limit": _human(limit)}
        )
    return int(size)


def declared_type(file: Any, key: str, content_type: str = "") -> str:
    """Return the client-declared type, or the one guessed from the key."""
    declared = content_type or getattr(file, "content_type", "") or ""
    return declared or mimetypes.guess_type(key)[0] or "application/octet-stream"


def check_type(content_type: str, accepted: Iterable[str]) -> None:
    """Refuse ``content_type`` unless it is in ``accepted``."""
    accepted = sorted(accepted)
    if content_type not in accepted:
        raise StorageError(
            _("File type not accepted: %(type)s. Accepted types: %(accepted)s.")
            % {"type": content_type, "accepted": ", ".join(accepted)}
        )


def check_signature(file: Any, content_type: str) -> None:
    """Refuse content whose magic bytes do not match ``content_type``."""
    rules = app_settings.ALLOWED_TYPES[content_type]
    file.seek(0)
    ends = [offset + len(magic) for offset, magic in rules if offset is not None]
    head = file.read(max([SIGNATURE_WINDOW, *ends]))
    for offset, magic in rules:
        if offset is None:
            matches = magic in head[:SIGNATURE_WINDOW]
        else:
            matches = head[offset : offset + len(magic)] == magic
        if not matches:
            raise StorageError(
                _("The file content does not match the type %(type)s.")
                % {"type": content_type}
            )


def check_image_pixels(file: Any) -> None:
    """Refuse images with too many pixels (``MAX_IMAGE_PIXELS``).

    A byte limit does not stop a decompression bomb: a flat-colour PNG of
    12000x12000 compresses to a few hundred KB and only shows its real size
    when something decodes it. ``Image.open`` reads only the header and
    ``.size`` does not decode, so this check is cheap.
    """
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise missing_dependency("pillow") from exc

    file.seek(0)
    try:
        with Image.open(file) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise StorageError(_("The uploaded image could not be read.")) from exc

    limit = app_settings.MAX_IMAGE_PIXELS
    if width * height > limit:
        raise StorageError(
            _(
                "The image is too large: %(width)dx%(height)d pixels. The limit "
                "is %(megapixels)s megapixels."
            )
            % {"width": width, "height": height, "megapixels": f"{limit / 1e6:g}"}
        )


def _human(size: int) -> str:
    """Return ``size`` as MB when it is at least 1 MiB, else as bytes."""
    mib = 1024 * 1024
    return f"{size // mib} MB" if size >= mib else f"{size} B"
