"""Defaults for the storage app, overridable through ``settings.TRIPAULX``.

``ALLOWED_TYPES`` is the upload policy: each accepted MIME type maps to the
magic-byte signatures its content must carry. A signature is an
``(offset, bytes)`` pair; every pair of a type must match. ``offset=None``
means "anywhere in the first ``SIGNATURE_WINDOW`` bytes" (PDFs written by
scanners and signing tools often carry a preamble before ``%PDF-``). Types
starting with ``image/`` are also measured with Pillow against
``MAX_IMAGE_PIXELS``. Never add SVG or HTML: both can carry scripts.
"""

from tripaulx.core.conf import AppSettings

MIB = 1024 * 1024

DEFAULT_ALLOWED_TYPES: dict[str, tuple[tuple[int | None, bytes], ...]] = {
    "application/pdf": ((None, b"%PDF-"),),
    "image/png": ((0, b"\x89PNG\r\n\x1a\n"),),
    "image/jpeg": ((0, b"\xff\xd8\xff"),),
    "image/webp": ((0, b"RIFF"), (8, b"WEBP")),
}

app_settings = AppSettings(
    {
        # Off by default: without credentials every call raises StorageError.
        "S3_ENABLED": False,
        "S3_ENDPOINT_URL": "",
        "S3_REGION": "",
        "S3_BUCKET": "",
        "S3_ACCESS_KEY": "",
        "S3_SECRET_KEY": "",
        # Lifetime of presigned download links, in seconds.
        "S3_URL_TTL": 900,
        "MAX_UPLOAD_BYTES": 25 * MIB,
        # Images get a smaller limit of their own (``upload_image``).
        "MAX_IMAGE_BYTES": 2 * MIB,
        # Decompression-bomb guard: width x height of any accepted image.
        "MAX_IMAGE_PIXELS": 4_000_000,
        # Master key (32 bytes, urlsafe base64). Empty stores files in clear.
        "FILE_ENCRYPTION_KEY": "",
        "ALLOWED_TYPES": DEFAULT_ALLOWED_TYPES,
    }
)
