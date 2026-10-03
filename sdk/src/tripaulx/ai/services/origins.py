"""Registry of execution origins (where a run came from).

Every event carries an ``origin`` used by the report and the event filters.
Instead of a hard-coded enum, the set is built from the built-in origins,
``TRIPAULX["AI_ORIGINS"]`` (value -> label) and :func:`register_origin`
calls (e.g. from a project's ``AppConfig.ready``)::

    from tripaulx.ai.services.origins import register_origin

    register_origin("invoice", _("Invoice editor"))
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from tripaulx.ai.conf import app_settings

PLAYGROUND = "playground"
TEST = "test"
API = "api"
OTHER = "other"

BUILTIN_ORIGINS = {
    PLAYGROUND: _("Playground"),
    TEST: _("Connection test"),
    API: _("API"),
    OTHER: _("Other"),
}

_registered: dict[str, str] = {}


def register_origin(value: str, label: str) -> None:
    """Add (or relabel) an origin."""
    _registered[value] = label


def origins() -> dict[str, str]:
    """Every origin value with its label."""
    merged = dict(BUILTIN_ORIGINS)
    merged.update(app_settings.AI_ORIGINS or {})
    merged.update(_registered)
    return {value: str(label) for value, label in merged.items()}


def label(value: str) -> str:
    """Label of ``value`` (the value itself when unknown)."""
    return origins().get(value, value)


def is_valid(value: str) -> bool:
    """Whether ``value`` is a known origin."""
    return value in origins()
