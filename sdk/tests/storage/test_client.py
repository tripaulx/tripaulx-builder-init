"""The cached boto3 client: disabled storage, provider config, missing deps."""

from __future__ import annotations

import sys
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from django.utils import translation

from tripaulx.storage.client import get_client, reset_client
from tripaulx.storage.exceptions import StorageError

from .helpers import CREDENTIALS, override_tripaulx


class ClientTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        reset_client()
        self.addCleanup(reset_client)

    def test_disabled_storage_explains_what_is_missing(self):
        with override_tripaulx(S3_ENABLED=False):
            with self.assertRaises(StorageError) as ctx:
                get_client()

        self.assertIn("S3_ACCESS_KEY", str(ctx.exception))

    def test_path_style_sigv4_and_no_new_checksums(self):
        with override_tripaulx(**CREDENTIALS), patch("boto3.client") as boto_client:
            get_client()

        _, kwargs = boto_client.call_args
        config = kwargs["config"]
        self.assertEqual(kwargs["endpoint_url"], "https://s3.example.com")
        self.assertEqual(kwargs["region_name"], "region-1")
        self.assertEqual(kwargs["aws_access_key_id"], "test-access-key")
        self.assertEqual(config.signature_version, "s3v4")
        self.assertEqual(config.s3["addressing_style"], "path")
        # Without this, non-AWS providers refuse uploads (aws-chunked trailer).
        self.assertEqual(config.request_checksum_calculation, "when_required")
        self.assertEqual(config.retries["max_attempts"], 3)

    def test_client_is_cached(self):
        with override_tripaulx(**CREDENTIALS), patch("boto3.client") as boto_client:
            self.assertIs(get_client(), get_client())

        self.assertEqual(boto_client.call_count, 1)

    def test_missing_boto3_fails_with_a_clear_message(self):
        with (
            override_tripaulx(**CREDENTIALS),
            patch.dict(sys.modules, {"boto3": None}),
        ):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                get_client()

        self.assertIn("tripaulx-sdk[storage]", str(ctx.exception))

    def test_errors_are_translated(self):
        with override_tripaulx(S3_ENABLED=False), translation.override("pt-br"):
            with self.assertRaises(StorageError) as ctx:
                get_client()

        self.assertIn("não está configurado", str(ctx.exception))
