"""Pipe tables with styling hooks for governance documents.

Hooks (CSS classes) the frontend can style:

- ``legal-table-wrap`` / ``legal-table``: the scroll wrapper and the table;
  ``legal-table--has-ids`` when the first column is an ``ID``.
- ``legal-id``: cells of that first ``ID`` column.
- ``legal-badge legal-badge-<level>``: a span around cells whose text holds a
  severity word of ``LEGAL_BADGE_WORDS`` (e.g. "Critical", "Alto").
- ``legal-score``: numeric cells under a ``LEGAL_SCORE_COLUMNS`` header.
"""

from __future__ import annotations

import re
import unicodedata

from ...conf import app_settings
from .inline import render_inline

_SEPARATOR_CELL = re.compile(r":?-{3,}:?")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def fold(value: str) -> str:
    """Lower-case ``value`` and strip accents, for predictable matching."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def row_cells(line: str) -> list[str]:
    """Split a ``| a | b |`` line into stripped cells."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator(line: str) -> bool:
    """Whether ``line`` is the ``|---|:---:|`` row under a table header."""
    cells = row_cells(line)
    return bool(cells) and all(_SEPARATOR_CELL.fullmatch(cell) for cell in cells)


def badge_level(value: str) -> str | None:
    """Return the severity level named in ``value``, if any."""
    folded = fold(value.strip())
    for level, words in app_settings.LEGAL_BADGE_WORDS.items():
        for word in words:
            if re.search(rf"\b{re.escape(fold(word))}\b", folded):
                return level
    return None


def _is_id_header(header: str) -> bool:
    folded = fold(header)
    return folded == "id" or folded.startswith("id ")


def _is_score_header(header: str) -> bool:
    folded = fold(header)
    return any(fold(word) in folded for word in app_settings.LEGAL_SCORE_COLUMNS)


def _cell_classes(value: str, column: int, headers: list[str]) -> list[str]:
    """Classes of a body cell (the badge goes on an inner span)."""
    classes: list[str] = []
    if column == 0 and headers and _is_id_header(headers[0]):
        classes.append("legal-id")
    if column < len(headers) and _is_score_header(headers[column]):
        if _NUMBER.fullmatch(value.strip()):
            classes.append("legal-score")
    return classes


def _class_attr(classes: list[str]) -> str:
    return f' class="{" ".join(classes)}"' if classes else ""


def _body_cell(value: str, column: int, headers: list[str]) -> str:
    content = render_inline(value)
    level = badge_level(value)
    if level:
        content = f'<span class="legal-badge legal-badge-{level}">{content}</span>'
    return f"<td{_class_attr(_cell_classes(value, column, headers))}>{content}</td>"


def _head_cell(value: str, column: int, headers: list[str]) -> str:
    classes = ["legal-table-head"]
    if column == 0 and _is_id_header(value):
        classes.append("legal-id")
    return f"<th{_class_attr(classes)}>{render_inline(value)}</th>"


def render_table(header: str, rows: list[str]) -> str:
    """Render a header line and its body lines as a wrapped table."""
    headers = row_cells(header)
    head = "".join(_head_cell(cell, i, headers) for i, cell in enumerate(headers))
    body = "".join(
        "<tr>"
        + "".join(_body_cell(cell, i, headers) for i, cell in enumerate(row_cells(r)))
        + "</tr>"
        for r in rows
    )
    table_class = "legal-table"
    if headers and _is_id_header(headers[0]):
        table_class += " legal-table--has-ids"
    return (
        f'<div class="legal-table-wrap"><table class="{table_class}">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )
