"""Object keys: always born inside the prefix of the connection's tenant."""

from __future__ import annotations

from django.test import SimpleTestCase

from tripaulx.storage import services as storage

from .helpers import StorageTestCase


class KeyTests(StorageTestCase):
    def test_key_starts_with_the_tenant_prefix(self):
        key = storage.build_key("invoices", "abc", name="report.pdf")

        self.assertTrue(key.startswith(f"tenants/{self.tenant.schema_name}/"))
        self.assertIn("invoices/abc/", key)
        self.assertTrue(key.endswith("-report.pdf"))

    def test_two_files_with_the_same_name_do_not_overwrite(self):
        first = storage.build_key("invoices", "x", name="report.pdf")
        second = storage.build_key("invoices", "x", name="report.pdf")

        self.assertNotEqual(first, second)

    def test_name_with_a_path_does_not_escape_the_prefix(self):
        # "../../etc/passwd" must become just "passwd", inside the tenant.
        key = storage.build_key("invoices", name="../../etc/passwd")

        self.assertTrue(key.startswith(f"tenants/{self.tenant.schema_name}/"))
        self.assertNotIn("..", key)
        self.assertTrue(key.endswith("-passwd"))

    def test_name_with_accents_and_spaces_becomes_safe(self):
        key = storage.build_key("invoices", name="Relatório Médico (final).pdf")

        self.assertNotIn(" ", key)
        self.assertRegex(key.rsplit("/", 1)[-1], r"^[A-Za-z0-9._-]+$")

    def test_key_without_parts_stays_in_the_tenant(self):
        key = storage.build_key(name="a.pdf")

        self.assertRegex(key, rf"^tenants/{self.tenant.schema_name}/[0-9a-f]{{12}}-a")

    def test_keys_of_another_tenant_are_refused(self):
        for key in (
            "tenants/other/invoices/x/report.pdf",
            f"tenants/{self.tenant.schema_name}-evil/x.pdf",
            f"tenants/{self.tenant.schema_name}/../other/x.pdf",
        ):
            with self.subTest(key=key):
                with self.assertRaises(storage.StorageError):
                    storage.ensure_tenant_key(key)


class CleanNameTests(SimpleTestCase):
    def test_windows_path_is_dropped(self):
        self.assertEqual(storage.clean_name("C:\\Users\\a\\doc.pdf"), "doc.pdf")

    def test_empty_or_dotted_name_gets_a_fallback(self):
        self.assertEqual(storage.clean_name(".."), "file")

    def test_long_name_is_cut(self):
        self.assertEqual(len(storage.clean_name("a" * 500 + ".pdf")), 120)


class DispositionTests(SimpleTestCase):
    def test_pdf_opens_inline(self):
        self.assertEqual(
            storage.content_disposition("My file.pdf", "application/pdf"),
            'inline; filename="My-file.pdf"',
        )

    def test_html_and_svg_never_open_inline(self):
        for kind in ("text/html", "image/svg+xml"):
            with self.subTest(kind=kind):
                self.assertTrue(
                    storage.content_disposition("x", kind).startswith("attachment")
                )
