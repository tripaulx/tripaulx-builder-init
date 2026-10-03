"""Inline Markdown: links, code, strong, emphasis and strike-through.

The text is HTML-escaped first; only the markup produced here is real HTML.
"""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from ..placeholders import PLACEHOLDER_RE

SAFE_SCHEMES = frozenset({"http", "https", "mailto"})

_LINK_RE = re.compile(r"\[([^\]]+)\]\((\S+)(?:\s+['\"]([^'\"]+)['\"])?\)")
_CODE_RE = re.compile(r"`([^`]+)`")
_STRONG_RE = re.compile(r"\*\*([^*]+)\*\*|__([^_]+)__")
_EM_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)|(?<!_)_([^_]+)_(?!_)")
_DEL_RE = re.compile(r"~~([^~]+)~~")


def safe_href(href: str) -> str | None:
    """Allow only explicit links without executable schemes.

    Accepted: ``http``, ``https``, ``mailto``, and scheme-less links starting
    with ``/`` or ``#``. Everything else (``javascript:``, ``data:``, bare
    relative paths) is refused.
    """
    parsed = urlparse(href)
    if parsed.scheme.casefold() in SAFE_SCHEMES:
        return href
    if not parsed.scheme and href.startswith(("/", "#")) and not href.startswith("//"):
        return href
    return None


def render_inline(value: str) -> str:
    """Render the small inline syntax used by the documents."""
    value = html.escape(value, quote=False)
    held: list[str] = []

    def hold(fragment: str) -> str:
        held.append(fragment)
        return f"\x00{len(held) - 1}\x00"

    def link(match: re.Match[str]) -> str:
        target = html.unescape(match.group(2))
        if safe_href(target) is None:
            return match.group(1)
        href = html.escape(target, quote=True)
        title = match.group(3)
        title_attr = f' title="{html.escape(title, quote=True)}"' if title else ""
        return hold(f'<a href="{href}"{title_attr}>{match.group(1)}</a>')

    value = _LINK_RE.sub(link, value)
    value = _CODE_RE.sub(lambda m: hold(f"<code>{m.group(1)}</code>"), value)
    # Unfilled placeholders are held so ``{{ a_b }} ... {{ c_d }}`` never
    # turns into emphasis, and get a hook to stand out.
    value = PLACEHOLDER_RE.sub(
        lambda m: hold(f'<span class="legal-placeholder">{m.group(0)}</span>'),
        value,
    )
    value = _STRONG_RE.sub(
        lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", value
    )
    value = _DEL_RE.sub(lambda m: f"<del>{m.group(1)}</del>", value)
    value = _EM_RE.sub(lambda m: f"<em>{m.group(1) or m.group(2)}</em>", value)
    for index, fragment in enumerate(held):
        value = value.replace(f"\x00{index}\x00", fragment)
    return value
