"""``{{ key }}`` placeholders of the document templates.

Values come from ``TRIPAULX["LEGAL_CONTEXT"]``; ``company`` and ``product``
fall back to ``APP_NAME``. A placeholder without a value (missing or empty)
stays in the text, so an unfinished document is visible to everyone and
``manage.py legal_check`` lists it.
"""

from __future__ import annotations

import re
from typing import Any

from tripaulx.core.conf import app_settings as core_settings

from ..conf import app_settings

PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")

#: Keys that fall back to ``TRIPAULX["APP_NAME"]`` when not set.
APP_NAME_KEYS = ("company", "product")


def context() -> dict[str, str]:
    """Return the placeholder values (only the non-empty ones)."""
    values: dict[str, Any] = dict.fromkeys(APP_NAME_KEYS, core_settings.APP_NAME)
    values.update(app_settings.LEGAL_CONTEXT or {})
    return {key: str(value) for key, value in values.items() if str(value).strip()}


def fill(text: str, values: dict[str, str] | None = None) -> str:
    """Replace every known placeholder of ``text``; leave the others as is."""
    values = context() if values is None else values

    def replace(match: re.Match[str]) -> str:
        return values.get(match.group(1), match.group(0))

    return PLACEHOLDER_RE.sub(replace, text)


def unfilled(text: str, values: dict[str, str] | None = None) -> list[str]:
    """Return the placeholder keys of ``text`` without a value, sorted."""
    values = context() if values is None else values
    keys = {match.group(1) for match in PLACEHOLDER_RE.finditer(text)}
    return sorted(keys - values.keys())
