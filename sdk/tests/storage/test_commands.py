"""``generate_file_key`` and ``check_bucket`` (against an in-memory bucket)."""

from __future__ import annotations

import base64
import io
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from .helpers import CREDENTIALS, KEY, StorageTestCase, override_tripaulx

URLOPEN = "tripaulx.storage.management.commands.check_bucket.urlopen"


class GenerateFileKeyTests(SimpleTestCase):
    def test_prints_a_32_byte_key(self):
        out = StringIO()

        call_command("generate_file_key", stdout=out)

        line = out.getvalue().splitlines()[0]
        name, _, value = line.partition("=")
        self.assertEqual(name, "FILE_ENCRYPTION_KEY")
        self.assertEqual(len(base64.urlsafe_b64decode(value)), 32)


class FakeBucket:
    """Just enough of the S3 API for ``check_bucket``."""

    def __init__(self):  # noqa: D107
        self.objects: dict[str, bytes] = {}
        self.client = MagicMock()
        self.client.upload_fileobj.side_effect = self.put
        self.client.get_object.side_effect = lambda Bucket, Key: {
            "Body": io.BytesIO(self.objects[Key])
        }
        self.client.generate_presigned_url.side_effect = lambda op, Params, ExpiresIn: (
            Params["Key"]
        )
        self.client.delete_object.side_effect = lambda Bucket, Key: self.objects.pop(
            Key
        )

    def put(self, body, bucket, key, **kwargs):
        self.objects[key] = body.read()

    def urlopen(self, url, **kwargs):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = self.objects[url]
        return response


class CheckBucketTests(StorageTestCase):
    def setUp(self):
        super().setUp()
        self.bucket = FakeBucket()
        self.enterContext(
            patch("tripaulx.storage.client.get_client", return_value=self.bucket.client)
        )
        self.enterContext(patch(URLOPEN, side_effect=self.bucket.urlopen))

    def run_command(self, *args: str) -> str:
        out = StringIO()
        call_command(
            "check_bucket", "--schema", self.tenant.schema_name, *args, stdout=out
        )
        return out.getvalue()

    def test_cycle_in_clear(self):
        output = self.run_command()

        self.assertIn("6/6 delete OK", output)
        self.assertEqual(self.bucket.objects, {})

    def test_cycle_with_encryption_proves_rest_and_round_trip(self):
        with override_tripaulx(FILE_ENCRYPTION_KEY=KEY):
            output = self.run_command()

        self.assertIn("4/6", output)
        self.assertIn("5/6", output)

    def test_keep_leaves_the_object(self):
        output = self.run_command("--keep")

        self.assertIn("object kept at", output)
        self.assertEqual(len(self.bucket.objects), 1)

    def test_plaintext_at_rest_fails_when_encryption_is_on(self):
        # A provider that "encrypts" but stores the plaintext must be caught.
        self.bucket.urlopen = lambda url, **kw: self._clear_response()
        self.enterContext(patch(URLOPEN, side_effect=self.bucket.urlopen))

        with override_tripaulx(FILE_ENCRYPTION_KEY=KEY):
            with self.assertRaises(CommandError):
                self.run_command()

    def _clear_response(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"%PDF-1.4 clear"
        return response

    def test_disabled_storage_is_a_command_error(self):
        with override_tripaulx(**{**CREDENTIALS, "S3_ENABLED": False}):
            with self.assertRaises(CommandError):
                self.run_command()
