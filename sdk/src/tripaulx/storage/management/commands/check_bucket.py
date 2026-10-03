"""Smoke-test the bucket end to end, against the real provider.

Runs the whole cycle with a throwaway object: upload, presigned link, download
through that link, content check and delete. It is how you know credentials,
endpoint and boto3 compatibility REALLY work; a mocked test would never catch,
for example, a provider rejecting boto3's default checksums.

Usage::

    manage.py check_bucket --schema acme
    manage.py check_bucket --schema acme --keep
"""

from __future__ import annotations

from datetime import UTC, datetime
import io
import ssl
from typing import Any
from urllib.request import urlopen

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django_tenants.utils import schema_context

from tripaulx.tenants.conf import app_settings as tenant_settings

from ... import crypto
from ... import services as storage
from ...conf import app_settings
from ...exceptions import StorageError

STEPS = 6


class Command(BaseCommand):
    """Upload, sign, download and delete a test object in the bucket."""

    help = "Check bucket access (upload + presigned link + download + delete)."

    def add_arguments(self, parser: CommandParser) -> None:
        """Declare --schema and --keep."""
        parser.add_argument(
            "--schema",
            default=tenant_settings.BOOTSTRAP_WORKSPACE or "public",
            help="Tenant schema whose key prefix is used.",
        )
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Keep the test object (to inspect it in the provider's console).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Run the cycle and report each step."""
        if not app_settings.S3_ENABLED:
            raise CommandError(
                "Storage is disabled: set S3_ENABLED, S3_ACCESS_KEY and "
                "S3_SECRET_KEY in TRIPAULX (APP_S3_* in the project's .env)."
            )
        self._log(
            f"bucket={app_settings.S3_BUCKET} "
            f"endpoint={app_settings.S3_ENDPOINT_URL} "
            f"region={app_settings.S3_REGION}"
        )
        now = datetime.now(UTC).isoformat(timespec="seconds")
        content = f"%PDF-1.4\nbucket access check {now}\n%%EOF\n".encode()
        encrypting = crypto.encryption_enabled()
        self._log(f"encryption: {'ON' if encrypting else 'off'}")

        with schema_context(options["schema"]):
            try:
                key = self._upload(content)
                raw = self._fetch(self._sign(key))
                if encrypting:
                    self._check_encrypted(raw, content)
                    self._check_decrypts(key, content)
                elif raw != content:
                    raise CommandError(
                        f"Downloaded content differs: expected {content!r}, "
                        f"got {raw!r}."
                    )
                if options["keep"]:
                    self._log(f"object kept at {key}")
                else:
                    storage.delete(key)
                    self._ok(6, "delete OK")
            except StorageError as exc:
                raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Bucket reachable: upload, presigned link, download and delete work."
            )
        )

    def _upload(self, content: bytes) -> str:
        """Upload the test PDF and return its key."""
        key = storage.build_key("_diagnostics", name="check.pdf")
        stored = storage.upload(io.BytesIO(content), key, "application/pdf")
        self._ok(1, f"upload OK -> {stored.key} ({stored.size} B)")
        return stored.key

    def _sign(self, key: str) -> str:
        """Return a presigned link to ``key``."""
        url = storage.temporary_url(key, download_name="check.pdf")
        self._ok(2, f"presigned link OK (expires in {app_settings.S3_URL_TTL}s)")
        return url

    def _fetch(self, url: str) -> bytes:
        """Download ``url`` with botocore's CA bundle (some Pythons lack system CAs)."""
        from botocore.httpsession import DEFAULT_CA_BUNDLE

        context = ssl.create_default_context(cafile=DEFAULT_CA_BUNDLE)
        with urlopen(url, timeout=30, context=context) as response:  # noqa: S310
            data = response.read()
        self._ok(3, f"download through the link OK ({len(data)} B)")
        return data

    def _check_encrypted(self, raw: bytes, clear: bytes) -> None:
        """Ensure what the BUCKET returns is unreadable: the proof of rest.

        Decrypting is not enough: had the object been stored in clear by
        mistake, the whole cycle would still pass.
        """
        if clear in raw or not crypto.is_encrypted(raw):
            raise CommandError(
                "The object in the bucket is NOT encrypted (the plaintext came "
                "back from the direct download)."
            )
        self._ok(4, "the stored object is unreadable (encrypted at rest)")

    def _check_decrypts(self, key: str, expected: bytes) -> None:
        """And the application must read it back, or we encrypted for nothing."""
        back = b"".join(storage.download(key))
        if back != expected:
            raise CommandError(
                f"Decryption did not return the original: expected {expected!r}, "
                f"got {back!r}."
            )
        self._ok(5, "the application decrypts and recovers the original")

    def _ok(self, step: int, message: str) -> None:
        """Print a successful step."""
        self.stdout.write(self.style.SUCCESS(f"  {step}/{STEPS} {message}"))

    def _log(self, message: str) -> None:
        """Print an informational line."""
        self.stdout.write(f"[check_bucket] {message}")
