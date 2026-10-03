"""Private S3-compatible object storage (``tripaulx.storage``).

Merged into ``TRIPAULX`` by the ``tripaulx`` chunk. Storage stays disabled
until both credentials are set, so the project runs without a bucket.
Upload types are a Python setting: add ``"ALLOWED_TYPES"`` here to change them
(defaults: PDF, PNG, JPEG and WebP; see ``tripaulx.storage.conf``).
"""

from .common import get_env, get_env_int

_ACCESS_KEY = get_env("APP_S3_ACCESS_KEY", "")
_SECRET_KEY = get_env("APP_S3_SECRET_KEY", "")

OBJECT_STORAGE = {
    "S3_ENABLED": bool(_ACCESS_KEY and _SECRET_KEY),
    "S3_ACCESS_KEY": _ACCESS_KEY,
    "S3_SECRET_KEY": _SECRET_KEY,
    "S3_BUCKET": get_env("APP_S3_BUCKET", ""),
    "S3_ENDPOINT_URL": get_env("APP_S3_ENDPOINT_URL", ""),
    "S3_REGION": get_env("APP_S3_REGION", ""),
    "S3_URL_TTL": get_env_int("APP_S3_URL_TTL", 900),
    "MAX_UPLOAD_BYTES": get_env_int("APP_S3_MAX_UPLOAD_BYTES", 25 * 1024 * 1024),
    "MAX_IMAGE_BYTES": get_env_int("APP_S3_MAX_IMAGE_BYTES", 2 * 1024 * 1024),
    "MAX_IMAGE_PIXELS": get_env_int("APP_S3_MAX_IMAGE_PIXELS", 4_000_000),
    # 32 bytes in urlsafe base64 (manage.py generate_file_key). Back it up:
    # losing it means losing every encrypted file.
    "FILE_ENCRYPTION_KEY": get_env("APP_FILE_ENCRYPTION_KEY", ""),
}
