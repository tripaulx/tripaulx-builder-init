"""Layered sanitization of the Markdown renderer (ported behaviour)."""

from django.test import SimpleTestCase

from tripaulx.legal.services import render_markdown, safe_href

UNSAFE = ("data:text/html,x", "//evil.example", "relative/path", "vbscript:x")
SAFE = ("https://example.com", "mailto:a@example.com", "/terms/", "#top")


class MarkdownSecurityTests(SimpleTestCase):
    def test_strips_active_html_and_keeps_formatting(self):
        html = render_markdown(
            "# Title\n\n**safe**\n\n<script>alert(1)</script>\n\n"
            "[link](https://example.com)"
        )

        assert "<h1>Title</h1>" in html
        assert "<strong>safe</strong>" in html
        assert "script" not in html.lower()
        assert 'rel="noopener noreferrer"' in html
        assert 'target="_blank"' in html

    def test_blocks_javascript_urls(self):
        html = render_markdown("[click](javascript:alert(1))")

        assert "javascript:" not in html.lower()
        assert "click" in html

    def test_blocks_other_unsafe_hrefs(self):
        for href in UNSAFE:
            assert safe_href(href) is None, href
            assert "<a" not in render_markdown(f"[x]({href})")

    def test_allows_safe_hrefs(self):
        for href in SAFE:
            assert safe_href(href) == href

    def test_internal_links_do_not_open_a_new_tab(self):
        html = render_markdown("[terms](/api/legal/public/terms-of-use/)")
        assert '<a href="/api/legal/public/terms-of-use/">terms</a>' in html

    def test_attribute_breakouts_and_raw_tags_are_neutralized(self):
        html = render_markdown(
            '[x](https://example.com/"onmouseover="alert(1))\n\n'
            "<img src=x onerror=alert(1)>"
        )
        assert 'onmouseover="' not in html
        assert "<img" not in html
        assert "onerror" not in html

    def test_code_blocks_are_escaped(self):
        html = render_markdown("```html\n<b>bold</b> & co\n```")
        assert '<code class="language-html">' in html
        assert "<b>" not in html

    def test_lists_quotes_and_rules(self):
        html = render_markdown("- a\n- b\n\n1. one\n2. two\n\n> quote\n\n---")
        assert "<ul><li>a</li><li>b</li></ul>" in html
        assert "<ol><li>one</li><li>two</li></ol>" in html
        assert "<blockquote><p>quote</p></blockquote>" in html
        assert "<hr>" in html

    def test_unfilled_placeholders_stand_out_and_never_become_emphasis(self):
        html = render_markdown("Contact {{ dpo_name }} at {{ dpo_email }}.")
        assert '<span class="legal-placeholder">{{ dpo_name }}</span>' in html
        assert "<em>" not in html
