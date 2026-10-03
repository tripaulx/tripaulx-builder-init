"""Limits and checks applied before anything reaches the bucket."""

from __future__ import annotations

import io

from django.core.files.uploadedfile import SimpleUploadedFile

from tripaulx.storage import services as storage
from tripaulx.storage.exceptions import StorageError

from .helpers import StorageTestCase, image_bytes, override_tripaulx, pdf

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class UploadTests(StorageTestCase):
    def key(self, name: str = "report.pdf") -> str:
        return storage.build_key("invoices", "x", name=name)

    def test_uploads_with_the_right_content_type(self):
        stored = storage.upload(pdf(), self.key())

        self.assertEqual(stored.content_type, "application/pdf")
        self.assertFalse(stored.encrypted)
        _, kwargs = self.client_mock.upload_fileobj.call_args
        self.assertEqual(kwargs["ExtraArgs"], {"ContentType": "application/pdf"})

    def test_type_outside_the_policy_is_refused_before_upload(self):
        refused = [
            SimpleUploadedFile("virus.exe", b"MZ", content_type="application/x-ms"),
            SimpleUploadedFile("note.txt", b"text", content_type="text/plain"),
            SimpleUploadedFile("doc.docx", b"PK\x03\x04", content_type=DOCX),
            SimpleUploadedFile("logo.svg", b"<svg/>", content_type="image/svg+xml"),
        ]
        for file in refused:
            with self.subTest(file=file.name):
                with self.assertRaises(StorageError) as ctx:
                    storage.upload(file, self.key(file.name))

                self.assertIn("File type not accepted", str(ctx.exception))

        self.client_mock.upload_fileobj.assert_not_called()

    def test_types_narrow_the_policy_for_one_call(self):
        png = SimpleUploadedFile("a.png", image_bytes(), content_type="image/png")

        with self.assertRaises(StorageError) as ctx:
            storage.upload(png, self.key("a.png"), types=["application/pdf"])

        self.assertIn("Accepted types: application/pdf", str(ctx.exception))
        self.client_mock.upload_fileobj.assert_not_called()

    def test_types_can_never_widen_the_policy(self):
        note = SimpleUploadedFile("n.txt", b"text", content_type="text/plain")

        with self.assertRaises(StorageError):
            storage.upload(note, self.key("n.txt"), types=["text/plain"])

    def test_policy_is_configurable(self):
        note = SimpleUploadedFile("n.txt", b"hello", content_type="text/plain")

        with override_tripaulx(ALLOWED_TYPES={"text/plain": ((0, b"hello"),)}):
            stored = storage.upload(note, self.key("n.txt"))
            with self.assertRaises(StorageError):
                storage.upload(pdf(), self.key())

        self.assertEqual(stored.content_type, "text/plain")

    def test_content_that_is_not_pdf_does_not_pass_on_content_type(self):
        # The content type comes from the client and proves nothing: renaming
        # a file is enough. The signature is what counts.
        disguised = pdf(content=b"MZ\x90\x00")

        with self.assertRaises(StorageError) as ctx:
            storage.upload(disguised, self.key())

        self.assertIn("does not match the type application/pdf", str(ctx.exception))
        self.client_mock.upload_fileobj.assert_not_called()

    def test_signature_may_follow_a_preamble(self):
        # Scanners and signing tools write bytes before the header; readers
        # open those files, so refusing them would refuse good documents.
        stored = storage.upload(pdf(content=b"\x00" * 500 + b"%PDF-1.7"), self.key())

        self.assertEqual(stored.content_type, "application/pdf")

    def test_signature_beyond_the_window_is_refused(self):
        # Past SIGNATURE_WINDOW there is no plausible PDF, only a marker hidden
        # in the middle to fool the check.
        late = pdf(content=b"\x00" * storage.SIGNATURE_WINDOW + b"%PDF-1.7")

        with self.assertRaises(StorageError):
            storage.upload(late, self.key())

    def test_signature_peek_does_not_eat_upload_bytes(self):
        # The check reads the start of the file; without rewinding, the bucket
        # would get a truncated file and nobody would notice until opening it.
        content = b"%PDF-1.4" + b"x" * 3000
        stored = self.capture_uploads()
        key = self.key()

        storage.upload(pdf(content=content), key)

        self.assertEqual(stored[key], content)

    def test_file_too_large_is_refused(self):
        with override_tripaulx(MAX_UPLOAD_BYTES=10):
            with self.assertRaises(StorageError):
                storage.upload(pdf(content=b"%PDF-" + b"x" * 50), self.key())

        self.client_mock.upload_fileobj.assert_not_called()

    def test_empty_file_is_refused(self):
        empty = SimpleUploadedFile("v.pdf", b"", content_type="application/pdf")

        with self.assertRaises(StorageError):
            storage.upload(empty, self.key("v.pdf"))

    def test_key_of_another_tenant_is_refused(self):
        with self.assertRaises(StorageError):
            storage.upload(pdf(), "tenants/other/x/report.pdf")

        self.client_mock.upload_fileobj.assert_not_called()

    def test_size_of_a_file_like_without_size(self):
        # Commands send a plain BytesIO (no Django ``.size``).
        content = b"%PDF-1.4\n"

        stored = storage.upload(io.BytesIO(content), self.key(), "application/pdf")

        self.assertEqual(stored.size, len(content))

    def test_provider_errors_become_storage_errors(self):
        self.client_mock.upload_fileobj.side_effect = RuntimeError("boom")

        with self.assertRaises(StorageError) as ctx:
            storage.upload(pdf(), self.key())

        self.assertIn("Failed to upload the file", str(ctx.exception))
