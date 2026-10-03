"""Validation rules shared by serializers, admin forms and services."""

from __future__ import annotations

import re
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

#: A host as web search tools accept it ("docs.example.com").
DOMAIN = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+"
)
#: Maximum domains per agent (the provider filters accept about 20).
MAX_SEARCH_DOMAINS = 20


def clean_search_domains(value: Any) -> list[str]:
    """Clean hosts: no scheme, path or slash; lower case; at most 20.

    Raises ``ValidationError`` for a non-list, an invalid host or too many.
    """
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValidationError(_("Enter a list of domains."))
    cleaned: list[str] = []
    for raw in value:
        host = str(raw or "").strip().lower()
        host = host.split("://", 1)[-1].split("/", 1)[0].split("?", 1)[0].strip(".")
        if not host:
            continue
        if not DOMAIN.fullmatch(host):
            raise ValidationError(_("Invalid domain: %(domain)s") % {"domain": raw})
        if host not in cleaned:
            cleaned.append(host)
    if len(cleaned) > MAX_SEARCH_DOMAINS:
        raise ValidationError(
            _("At most %(count)s web search domains.") % {"count": MAX_SEARCH_DOMAINS}
        )
    return cleaned


def clean_output_schema(value: Any) -> dict:
    """Empty, or a JSON Schema of an object (``type: object``)."""
    if value in (None, {}):
        return {}
    if not isinstance(value, dict) or value.get("type") != "object":
        raise ValidationError(
            _("The output schema must be a JSON Schema of an object (type: object).")
        )
    return value


def clean_temperature(value: Any) -> Any:
    """Temperature goes from 0 to 2 (or is empty)."""
    if value is not None and not 0 <= value <= 2:
        raise ValidationError(_("Temperature goes from 0 to 2."))
    return value
