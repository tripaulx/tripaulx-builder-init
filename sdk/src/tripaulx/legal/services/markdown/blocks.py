"""Block-level Markdown: headings, code, rules, quotes, tables, lists, text.

A hand-written subset, enough for policy and governance documents. Each
parser takes the lines and the current index and returns the HTML plus the
next index, or ``None`` when the block does not start there.
"""

from __future__ import annotations

from collections.abc import Callable
import html
import re

from .inline import render_inline
from .tables import is_separator, render_table

Block = tuple[str, int] | None

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
_RULE = re.compile(r"\s*(\*\s*){3,}|(-\s*){3,}|(_\s*){3,}")
_BULLET = re.compile(r"^\s*[-*+]\s+(.+)$")
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.+)$")
_PARAGRAPH_END = re.compile(
    r"^(#{1,6})\s+|^```|^\s*[-*+]\s+|^\s*\d+[.)]\s+|^\s*>|^\s*\|"
)


def _code(lines: list[str], index: int) -> Block:
    if not lines[index].startswith("```"):
        return None
    language = html.escape(lines[index][3:].strip(), quote=True)
    code: list[str] = []
    index += 1
    while index < len(lines) and not lines[index].startswith("```"):
        code.append(lines[index])
        index += 1
    class_attr = f' class="language-{language}"' if language else ""
    body = html.escape("\n".join(code))
    return f"<pre><code{class_attr}>{body}</code></pre>", index + 1


def _heading(lines: list[str], index: int) -> Block:
    match = _HEADING.match(lines[index])
    if not match:
        return None
    level = len(match.group(1))
    return f"<h{level}>{render_inline(match.group(2))}</h{level}>", index + 1


def _rule(lines: list[str], index: int) -> Block:
    return ("<hr>", index + 1) if _RULE.fullmatch(lines[index]) else None


def _quote(lines: list[str], index: int) -> Block:
    if not lines[index].lstrip().startswith(">"):
        return None
    quote: list[str] = []
    while index < len(lines) and lines[index].lstrip().startswith(">"):
        quote.append(lines[index].lstrip()[1:].lstrip())
        index += 1
    return f"<blockquote><p>{render_inline(' '.join(quote))}</p></blockquote>", index


def _table(lines: list[str], index: int) -> Block:
    line = lines[index]
    if "|" not in line or index + 1 >= len(lines) or not is_separator(lines[index + 1]):
        return None
    rows: list[str] = []
    index += 2
    while index < len(lines) and "|" in lines[index] and lines[index].strip():
        rows.append(lines[index])
        index += 1
    return render_table(line, rows), index


def _list(lines: list[str], index: int) -> Block:
    ordered = _NUMBERED.match(lines[index]) is not None
    if not ordered and not _BULLET.match(lines[index]):
        return None
    pattern = _NUMBERED if ordered else _BULLET
    items: list[str] = []
    while index < len(lines):
        match = pattern.match(lines[index])
        if not match:
            break
        items.append(f"<li>{render_inline(match.group(1))}</li>")
        index += 1
    tag = "ol" if ordered else "ul"
    return f"<{tag}>{''.join(items)}</{tag}>", index


def _paragraph(lines: list[str], index: int) -> Block:
    text = [lines[index].strip()]
    index += 1
    while (
        index < len(lines)
        and lines[index].strip()
        and not _PARAGRAPH_END.match(lines[index])
    ):
        text.append(lines[index].strip())
        index += 1
    return f"<p>{render_inline(' '.join(text))}</p>", index


PARSERS: tuple[Callable[[list[str], int], Block], ...] = (
    _code,
    _heading,
    _rule,
    _quote,
    _table,
    _list,
    _paragraph,
)


def render_blocks(source: str) -> str:
    """Render the Markdown subset of ``source`` as (unsanitized) HTML."""
    lines = source.replace("\r\n", "\n").split("\n")
    output: list[str] = []
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        for parser in PARSERS:
            block = parser(lines, index)
            if block is not None:
                output.append(block[0])
                index = block[1]
                break
    return "\n".join(output)
