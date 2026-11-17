"""Sample contexts of the e-mail templates, for previews and test sends.

The SDK's own e-mails are registered here; a project adds its own with
:func:`register_sample` (typically from an ``AppConfig.ready``)::

    register_sample("monthly_report", lambda: {"client": "Acme Ltda"})
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

SampleFactory = Callable[[], dict[str, Any]]

_SAMPLE_CODE = "482915"


def _code() -> dict[str, Any]:
    """Context of the e-mails that carry a one-time code."""
    return {
        "user": None,
        "first_name": "Ana",
        "code": _SAMPLE_CODE,
        "code_spaced": " ".join(_SAMPLE_CODE),
        "minutes": 10,
    }


def _invite() -> dict[str, Any]:
    """Context of the invitation e-mail."""
    return {
        "url": "https://acme.example.com/accept-invitation?token=sample",
        "inviter": "ana@example.com",
        "workspace": "Acme Ltda",
        "days": 7,
    }


_samples: dict[str, SampleFactory] = {
    "email_verify": _code,
    "login_2fa": _code,
    "password_reset": _code,
    "invite": _invite,
}


def register_sample(name: str, factory: SampleFactory) -> None:
    """Register (or replace) the sample context of the e-mail ``name``."""
    _samples[name] = factory


def sample_names() -> tuple[str, ...]:
    """Return the names of the e-mails that have a sample, sorted."""
    return tuple(sorted(_samples))


def sample_context(name: str) -> dict[str, Any]:
    """Return a realistic context for the e-mail ``name``.

    Raises:
        KeyError: no sample is registered under ``name``.
    """
    return _samples[name]()
