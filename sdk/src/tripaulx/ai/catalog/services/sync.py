"""Load or update the catalog from a JSON or TOML file.

The file holds a list of models under the ``models`` key (JSON may also be a
bare list). Each entry uses the :class:`AIModel` field names; ``provider`` and
``identifier`` are required and identify the row::

    [[models]]
    provider = "openai"
    identifier = "gpt-6.1-sol"
    label = "GPT-6.1 Sol"
    input_price_usd_1m = "2.00"
    cached_price_usd_1m = "0.10"
    output_price_usd_1m = "10.00"

New rows are created; existing rows get the given fields only, so a file with
prices alone never wipes a description edited in the admin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import tomllib
from typing import Any

from django.db import transaction
from django.utils.translation import gettext as _

from tripaulx.ai.catalog.models import AIModel

PRICE_FIELDS = ("input_price_usd_1m", "cached_price_usd_1m", "output_price_usd_1m")
EDITABLE_FIELDS = frozenset(
    f.name
    for f in AIModel._meta.get_fields()
    if getattr(f, "editable", False)
    and f.name not in {"id", "provider", "identifier", "created_at", "updated_at"}
)


class CatalogFileError(ValueError):
    """The file cannot be read or holds an invalid entry."""


@dataclass
class SyncResult:
    """What a sync did."""

    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)


def read_entries(path: Path) -> list[dict[str, Any]]:
    """Parse ``path`` (``.json`` or ``.toml``) into a list of entries."""
    try:
        raw = path.read_bytes()
        if path.suffix.lower() == ".toml":
            data: Any = tomllib.loads(raw.decode())
        else:
            data = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise CatalogFileError(
            _("Cannot read %(path)s: %(error)s") % {"path": path, "error": exc}
        ) from exc
    entries = data.get("models") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise CatalogFileError(_("The file must hold a list of models."))
    return entries


def _clean(entry: Any, *, prices_only: bool) -> tuple[str, str, dict[str, Any]]:
    """Validate one entry; return ``(provider, identifier, fields)``."""
    if not isinstance(entry, dict):
        raise CatalogFileError(_("Every model must be an object."))
    provider = str(entry.get("provider") or "").strip()
    identifier = str(entry.get("identifier") or "").strip()
    if not provider or not identifier:
        raise CatalogFileError(_("Every model needs a provider and an identifier."))
    allowed = set(PRICE_FIELDS) | {"prices_updated_on"}
    if not prices_only:
        allowed |= EDITABLE_FIELDS
    unknown = set(entry) - allowed - {"provider", "identifier"}
    if unknown and not prices_only:
        raise CatalogFileError(
            _("Unknown fields in %(model)s: %(fields)s")
            % {"model": identifier, "fields": ", ".join(sorted(unknown))}
        )
    fields = {k: v for k, v in entry.items() if k in allowed}
    for name in PRICE_FIELDS:
        if fields.get(name) is not None:
            try:
                fields[name] = Decimal(str(fields[name]))
            except InvalidOperation as exc:
                raise CatalogFileError(
                    _("Invalid price %(field)s in %(model)s.")
                    % {"field": name, "model": identifier}
                ) from exc
    return provider, identifier, fields


def sync(entries: list[dict[str, Any]], *, prices_only: bool = False) -> SyncResult:
    """Create or update the catalog rows from ``entries`` atomically."""
    cleaned = [_clean(entry, prices_only=prices_only) for entry in entries]
    result = SyncResult()
    with transaction.atomic():
        for provider, identifier, fields in cleaned:
            row = AIModel.objects.filter(
                provider=provider, identifier=identifier
            ).first()
            name = f"{provider}:{identifier}"
            if row is None:
                if prices_only:
                    continue
                fields.setdefault("label", identifier)
                AIModel.objects.create(
                    provider=provider, identifier=identifier, **fields
                )
                result.created.append(name)
                continue
            for key, value in fields.items():
                setattr(row, key, value)
            row.save()
            result.updated.append(name)
    return result
