"""Presigned links, deletion and downloads, and refusing other tenants' keys."""

from __future__ import annotations

import io

from tripaulx.storage import crypto
from tripaulx.storage import services as storage
from tripaulx.storage.exceptions import StorageError

from .helpers import KEY, StorageTestCase, override_tripaulx, pdf

FOREIGN = "tenants/other/invoices/x/report.pdf"


class LinkAndDeleteTests(StorageTestCase):
    def setUp(self):
        super().setUp()
        self.client_mock.generate_presigned_url.return_value = "https://signed"

    def test_presigned_link_expires_and_carries_the_original_name(self):
        key = storage.build_key("invoices", "x", name="report.pdf")

        url = storage.temporary_url(key, download_name="Final report.pdf")

        self.assertEqual(url, "https://signed")
        _, kwargs = self.client_mock.generate_presigned_url.call_args
        self.assertEqual(kwargs["ExpiresIn"], 900)
        disposition = kwargs["Params"]["ResponseContentDisposition"]
        self.assertEqual(disposition, 'attachment; filename="Final-report.pdf"')

    def test_link_with_an_inline_type_opens_in_the_tab(self):
        key = storage.build_key("invoices", name="report.pdf")

        storage.temporary_url(
            key, download_name="report.pdf", content_type="application/pdf"
        )

        params = self.client_mock.generate_presigned_url.call_args.kwargs["Params"]
        self.assertTrue(params["ResponseContentDisposition"].startswith("inline"))
        self.assertEqual(params["ResponseContentType"], "application/pdf")

    def test_does_not_sign_a_link_to_another_tenants_file(self):
        # Last line of defence: even if the key comes tampered from the DB.
        with self.assertRaises(StorageError):
            storage.temporary_url(FOREIGN)

        self.client_mock.generate_presigned_url.assert_not_called()

    def test_does_not_delete_another_tenants_file(self):
        with self.assertRaises(StorageError):
            storage.delete(FOREIGN)

        self.client_mock.delete_object.assert_not_called()

    def test_does_not_read_another_tenants_file(self):
        with self.assertRaises(StorageError):
            list(storage.download(FOREIGN))

        self.client_mock.get_object.assert_not_called()

    def test_deletes_its_own_file(self):
        key = storage.build_key("invoices", "x", name="report.pdf")

        storage.delete(key)

        _, kwargs = self.client_mock.delete_object.call_args
        self.assertEqual(kwargs, {"Bucket": "acme-files", "Key": key})


class EncryptedRoundTripTests(StorageTestCase):
    """Upload with a master key, then download through the application."""

    def setUp(self):
        super().setUp()
        self.enterContext(override_tripaulx(FILE_ENCRYPTION_KEY=KEY))
        self.stored = self.capture_uploads()
        self.client_mock.get_object.side_effect = lambda Bucket, Key: {
            "Body": io.BytesIO(self.stored[Key])
        }

    def test_bucket_only_sees_ciphertext(self):
        content = b"%PDF-1.4 confidential body"
        key = storage.build_key("invoices", name="report.pdf")

        result = storage.upload(pdf(content=content), key)

        self.assertTrue(result.encrypted)
        self.assertNotIn(b"confidential", self.stored[key])
        self.assertTrue(crypto.is_encrypted(self.stored[key]))
        extra = self.client_mock.upload_fileobj.call_args.kwargs["ExtraArgs"]
        self.assertEqual(extra, {"ContentType": "application/octet-stream"})

    def test_download_decrypts(self):
        content = b"%PDF-1.4 " + b"y" * (crypto.CHUNK + 10)
        key = storage.build_key("invoices", name="report.pdf")
        storage.upload(pdf(content=content), key)

        self.assertEqual(b"".join(storage.download(key)), content)

    def test_plaintext_objects_are_still_served(self):
        # Objects uploaded while no master key was set come back as they are.
        key = storage.build_key("invoices", name="old.pdf")
        self.stored[key] = b"%PDF-1.4 stored in clear"

        self.assertEqual(b"".join(storage.download(key)), self.stored[key])

    def test_tiny_plaintext_object_is_served(self):
        key = storage.build_key("invoices", name="t.txt")
        self.stored[key] = b"ab"

        self.assertEqual(b"".join(storage.download(key)), b"ab")
