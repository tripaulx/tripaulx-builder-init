"""Safe Markdown to HTML conversion, in layers.

1. Raw HTML tags are stripped from the source (documents are Markdown only).
2. Every piece of text is HTML-escaped; links pass :func:`safe_href`.
3. The result goes through the ``nh3`` allowlist of tags and attributes.
4. External links get ``rel="noopener noreferrer"`` and ``target="_blank"``.
"""

from __future__ import annotations

import re

import nh3

from .blocks import render_blocks
from .inline import SAFE_SCHEMES, render_inline, safe_href

__all__ = ["render_inline", "render_markdown", "safe_href"]

ALLOWED_TAGS = frozenset(
    {
        "a",
        "blockquote",
        "br",
        "code",
        "del",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "li",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
)
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "code": {"class"},
    "div": {"class"},
    "span": {"class"},
    "table": {"class"},
    "td": {"align", "class", "colspan", "rowspan"},
    "th": {"align", "class", "colspan", "rowspan"},
    "tr": {"class"},
}

_RAW_TAG = re.compile(r"<[^>]*>")
_EXTERNAL_LINK = re.compile(r"<a(?P<attrs>[^>]*)href=\"(?P<href>https?://[^\"]+)\"")


def _secure_link(match: re.Match[str]) -> str:
    """Open external links in a new tab without handing over ``window.opener``."""
    attrs, href = match.group("attrs"), match.group("href")
    rel = "" if " rel=" in attrs else ' rel="noopener noreferrer"'
    target = "" if " target=" in attrs else ' target="_blank"'
    return f'<a{attrs}href="{href}"{rel}{target}'


def render_markdown(source: str) -> str:
    """Render document Markdown as HTML with no active content."""
    # Stripping tags up front keeps ``<script>`` from even showing up as text
    # and makes the rule independent of any parser behaviour.
    source = _RAW_TAG.sub("", source.replace("\x00", ""))
    cleaned = nh3.clean(
        render_blocks(source),
        tags=set(ALLOWED_TAGS),
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=set(SAFE_SCHEMES),
        link_rel=None,
    )
    return _EXTERNAL_LINK.sub(_secure_link, cleaned)
