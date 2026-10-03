"""Access to SDK options stored in the ``TRIPAULX`` settings dict.

Each SDK app declares its defaults with :class:`AppSettings`; projects override
any key in ``settings.TRIPAULX``. Values are read on every access so tests can
use ``override_settings(TRIPAULX={...})``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.conf import settings

SETTINGS_NAME = "TRIPAULX"


class AppSettings:
    """Attribute-style view over ``settings.TRIPAULX`` with app defaults."""

    def __init__(self, defaults: Mapping[str, Any]) -> None:
        """Store the defaults; keys are upper-case option names."""
        self._defaults = dict(defaults)

    def __getattr__(self, name: str) -> Any:
        """Return the project value for ``name`` or the app default."""
        if name.startswith("_") or name not in self._defaults:
            raise AttributeError(name)
        overrides = getattr(settings, SETTINGS_NAME, {}) or {}
        return overrides.get(name, self._defaults[name])
