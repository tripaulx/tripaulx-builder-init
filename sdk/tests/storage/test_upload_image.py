"""The separate image door: ``image/*`` policy types and their own limits."""

from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile

from tripaulx.storage import services as storage
from tripaulx.storage.conf import app_settings
from tripaulx.storage.exceptions import StorageError

from .helpers import StorageTestCase, image_bytes, override_tripaulx, pdf


def image(name: str, content: bytes, kind: str = "image/png"):
    return SimpleUploadedFile(name, content, content_type=kind)


class UploadImageTests(StorageTestCase):
    def key(self, name: str = "logo.png") -> str:
        return storage.build_key("branding", name=name)

    def test_png_jpeg_and_webp_are_accepted(self):
        cases = [
            ("logo.png", image_bytes(fmt="PNG"), "image/png"),
            ("sign.jpg", image_bytes(fmt="JPEG"), "image/jpeg"),
            ("pic.webp", image_bytes(fmt="WEBP"), "image/webp"),
        ]
        for name, content, kind in cases:
            with self.subTest(name=name):
                stored = storage.upload_image(
                    image(name, content, kind), self.key(name)
                )

                self.assertEqual(stored.content_type, kind)
                self.assertEqual(stored.size, len(content))

    def test_pdf_does_not_enter_through_the_image_door(self):
        with self.assertRaises(StorageError) as ctx:
            storage.upload_image(pdf(), self.key("report.pdf"))

        self.assertIn("File type not accepted", str(ctx.exception))
        self.client_mock.upload_fileobj.assert_not_called()

    def test_disguised_content_is_refused(self):
        with self.assertRaises(StorageError):
            storage.upload_image(image("logo.png", b"MZ\x90\x00"), self.key())

        self.client_mock.upload_fileobj.assert_not_called()

    def test_image_signature_must_be_at_offset_zero(self):
        # Valid images have no preamble (unlike scanned PDFs): accepting junk
        # in front would only make room for polyglot files.
        junk = b"\x00" * 8 + b"\x89PNG\r\n\x1a\n"

        with self.assertRaises(StorageError):
            storage.upload_image(image("logo.png", junk), self.key())

    def test_webp_needs_both_riff_and_webp_markers(self):
        riff_only = b"RIFF\x00\x00\x00\x00WAVEfmt "

        with self.assertRaises(StorageError):
            storage.upload_image(image("a.webp", riff_only, "image/webp"), self.key())

    def test_svg_is_refused(self):
        with self.assertRaises(StorageError):
            storage.upload_image(
                image("logo.svg", b"<svg/>", "image/svg+xml"), self.key("logo.svg")
            )

    def test_image_limit_is_its_own_not_the_upload_one(self):
        big = image("logo.png", b"\x89PNG\r\n\x1a\n" + b"x" * 500)

        with override_tripaulx(MAX_IMAGE_BYTES=10):
            with self.assertRaises(StorageError):
                storage.upload_image(big, self.key())
            # The same size passes easily through the general door.
            storage.upload(pdf(content=b"%PDF-1.4" + b"x" * 500), self.key("a.pdf"))

    def test_image_with_too_many_pixels_is_refused(self):
        """The decompression bomb: few bytes, many pixels."""
        bomb = image("logo.png", image_bytes(3000, 3000))
        # Few bytes: it would pass the byte limit easily.
        self.assertLess(bomb.size, app_settings.MAX_IMAGE_BYTES)

        with self.assertRaises(StorageError) as ctx:
            storage.upload_image(bomb, self.key())

        self.assertIn("megapixels", str(ctx.exception))
        self.client_mock.upload_fileobj.assert_not_called()

    def test_pixel_limit_also_guards_the_general_door(self):
        bomb = image("logo.png", image_bytes(3000, 3000))

        with self.assertRaises(StorageError):
            storage.upload(bomb, self.key())

    def test_image_within_the_pixel_limit_is_accepted(self):
        inside = image("logo.png", image_bytes(1200, 800))

        self.assertEqual(
            storage.upload_image(inside, self.key()).content_type, "image/png"
        )

    def test_image_header_followed_by_junk_is_refused(self):
        """Right magic bytes, no actual image: it cannot be measured."""
        junk = image("logo.png", b"\x89PNG\r\n\x1a\nnot-a-png")

        with self.assertRaises(StorageError) as ctx:
            storage.upload_image(junk, self.key())

        self.assertIn("could not be read", str(ctx.exception))

    def test_empty_image_is_refused(self):
        with self.assertRaises(StorageError):
            storage.upload_image(image("logo.png", b""), self.key())

    def test_peeks_do_not_eat_upload_bytes(self):
        # Two peeks before the upload (signature and dimensions): if either
        # did not rewind, the bucket would get a truncated image.
        content = image_bytes(64, 64)
        stored = self.capture_uploads()
        key = self.key()

        storage.upload_image(image("logo.png", content), key)

        self.assertEqual(stored[key], content)
