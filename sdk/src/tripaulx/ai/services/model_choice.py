"""The one rule for choosing a model: an active catalog row of the provider.

Used by the settings, agent and skill serializers and by the admin, so the
rule lives in one place.
"""

from __future__ import annotations

from django.utils.translation import gettext as _

from tripaulx.ai import providers
from tripaulx.ai.catalog import services as catalog
from tripaulx.ai.models import AISettings


class InvalidModelChoice(ValueError):
    """The model cannot be chosen; the message says why."""


def check_provider(provider: str) -> str:
    """Return ``provider`` when it is registered, else raise."""
    if providers.get_provider(provider) is None:
        raise InvalidModelChoice(
            _("Unknown provider: %(provider)s.") % {"provider": provider}
        )
    return provider


def check(identifier: str, provider: str | None = None) -> str:
    """Return ``identifier`` when it can be chosen now, else raise.

    Empty means "inherit" and is always accepted. ``provider`` defaults to
    the one of the workspace settings.
    """
    identifier = (identifier or "").strip()
    if not identifier:
        return ""
    provider = provider or AISettings.load().provider
    model = catalog.find(provider, identifier)
    if model is None:
        raise InvalidModelChoice(
            _("“%(model)s” is not a catalog model of %(provider)s.")
            % {"model": identifier, "provider": providers.label_of(provider)}
        )
    if not model.active:
        raise InvalidModelChoice(
            _("The model “%(model)s” is inactive and cannot be chosen.")
            % {"model": model.label}
        )
    return identifier
