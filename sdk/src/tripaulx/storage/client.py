"""Cached boto3 client for the private, S3-compatible bucket.

Most S3-compatible providers need three things boto3 does not guess:

1. ``addressing_style="path"``: URLs are ``<endpoint>/<bucket>/<key>`` rather
   than the virtual-host style (``<bucket>.<endpoint>/<key>``) boto3 defaults
   to.
2. SigV4 signatures.
3. **No new default checksums.** Since botocore 1.36 the SDK sends a CRC32
   trailer with ``Content-Encoding: aws-chunked`` on every upload. Many
   non-AWS providers do not understand that format and reject the upload with
   a misleading ``AccessDenied`` (the credentials are fine; the body looks
   odd). ``request_checksum_calculation="when_required"`` turns it off without
   pinning boto3 below 1.36 forever.

When storage is disabled (``S3_ENABLED`` false) every use raises
:class:`StorageError` instead of an obscure boto3 error, so tests and local
development never talk to the cloud.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from django.utils.translation import gettext as _

from .conf import app_settings
from .exceptions import StorageError, missing_dependency


@lru_cache(maxsize=1)
def get_client() -> Any:
    """Return the bucket's boto3 client, built once per process.

    A boto3 client is safe to reuse across requests (creating sessions is what
    is not thread-safe) and building one is expensive, hence the cache.
    """
    if not app_settings.S3_ENABLED:
        raise StorageError(
            _(
                "Object storage is not configured: set S3_ENABLED, "
                "S3_ACCESS_KEY and S3_SECRET_KEY in TRIPAULX."
            )
        )
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise missing_dependency("boto3") from exc

    config = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
        # See the module docstring: without this, non-AWS providers refuse
        # every upload.
        request_checksum_calculation="when_required",
        response_checksum_validation="when_supported",
        retries={"max_attempts": 3, "mode": "standard"},
    )
    return boto3.client(
        "s3",
        endpoint_url=app_settings.S3_ENDPOINT_URL or None,
        region_name=app_settings.S3_REGION or None,
        aws_access_key_id=app_settings.S3_ACCESS_KEY,
        aws_secret_access_key=app_settings.S3_SECRET_KEY,
        config=config,
    )


def reset_client() -> None:
    """Drop the cached client (tests, or after changing credentials)."""
    get_client.cache_clear()
