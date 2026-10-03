"""Shared helpers for the storage tests (no network: boto3 is always mocked)."""

from __future__ import annotations

import base64
import io
from typing import Any
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from tripaulx.core.testing import TenantTestCase
from tripaulx.storage.client import reset_client

CREDENTIALS = {
    "S3_ENABLED": True,
    "S3_ENDPOINT_URL": "https://s3.example.com",
    "S3_REGION": "region-1",
    "S3_ACCESS_KEY": "test-access-key",
    "S3_SECRET_KEY": "test-secret-key",
    "S3_BUCKET": "acme-files",
}
KEY = base64.urlsafe_b64encode(b"k" * 32).decode()
OTHER_KEY = base64.urlsafe_b64encode(b"x" * 32).decode()


class override_tripaulx(override_settings):  # noqa: N801 (mirrors Django's API)
    """``override_settings`` for single ``TRIPAULX`` keys.

    The dict is merged when the override is ENTERED, so nested overrides keep
    the keys set by the outer ones (e.g. the conftest's blank file key).
    """

    def __init__(self, **options: Any) -> None:  # noqa: D107
        self._tripaulx = options
        super().__init__()

    def enable(self) -> None:
        self.options = {"TRIPAULX": {**settings.TRIPAULX, **self._tripaulx}}
        super().enable()


def pdf(name: str = "report.pdf", content: bytes = b"%PDF-1.4 fake"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def image_bytes(width: int = 8, height: int = 8, fmt: str = "PNG") -> bytes:
    """Return a REAL image: the policy opens the file to measure it."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (10, 20, 30)).save(buffer, format=fmt)
    return buffer.getvalue()


class StorageTestCase(TenantTestCase):
    """Tenant test with credentials set and a mocked boto3 client."""

    def setUp(self) -> None:
        super().setUp()
        self.enterContext(override_tripaulx(**CREDENTIALS))
        reset_client()
        self.addCleanup(reset_client)
        self.client_mock = MagicMock()
        self.enterContext(
            patch("tripaulx.storage.client.get_client", return_value=self.client_mock)
        )

    def capture_uploads(self) -> dict[str, bytes]:
        """Record what each ``upload_fileobj`` call would store, by key."""
        stored: dict[str, bytes] = {}
        self.client_mock.upload_fileobj.side_effect = lambda body, _bucket, key, **kw: (
            stored.__setitem__(key, body.read())
        )
        return stored
