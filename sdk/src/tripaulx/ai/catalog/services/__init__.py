"""Catalog lookups: the single place that resolves ``provider + identifier``.

The catalog table lives in the public schema. Tenant connections keep
``public`` in their ``search_path``, so these queries work from any schema
without switching to it.
"""

from __future__ import annotations

from tripaulx.ai.catalog.models import AIModel


def find(provider: str, identifier: str) -> AIModel | None:
    """Return the row of ``provider`` + ``identifier`` (active or not)."""
    if not provider or not identifier:
        return None
    return AIModel.objects.filter(provider=provider, identifier=identifier).first()


def find_active(provider: str, identifier: str) -> AIModel | None:
    """Like :func:`find`, but only an active row counts."""
    model = find(provider, identifier)
    return model if model is not None and model.active else None


def active_by_provider() -> dict[str, list[AIModel]]:
    """Active models grouped by provider, in display order (one query)."""
    grouped: dict[str, list[AIModel]] = {}
    for model in AIModel.objects.filter(active=True):
        grouped.setdefault(model.provider, []).append(model)
    return grouped
