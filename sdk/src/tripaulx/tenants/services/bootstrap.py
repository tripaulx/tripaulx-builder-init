"""Idempotent creation of the public schema and an initial workspace."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from django.conf import settings

from ..models import Domain, Workspace


@dataclass(frozen=True)
class DomainResult:
    """Outcome of ensuring one domain."""

    domain: str
    created: bool
    conflict: bool = False


def ensure_workspace(schema: str, name: str) -> tuple[Workspace, bool]:
    """Get or create the workspace ``schema`` (creating its schema if new)."""
    return Workspace.objects.get_or_create(schema_name=schema, defaults={"name": name})


def ensure_public() -> tuple[Workspace, bool]:
    """Get or create the workspace row that represents the public schema."""
    return ensure_workspace(settings.PUBLIC_SCHEMA_NAME, "Public")


def ensure_domain(domain: str, workspace: Workspace, *, primary: bool) -> DomainResult:
    """Point ``domain`` at ``workspace``; never steal a domain from another one."""
    obj, created = Domain.objects.get_or_create(
        domain=domain, defaults={"tenant": workspace, "is_primary": primary}
    )
    if not created and obj.tenant_id != workspace.pk:
        return DomainResult(domain, created=False, conflict=True)
    if not created and obj.is_primary != primary:
        obj.is_primary = primary
        obj.save(update_fields=["is_primary"])
    return DomainResult(domain, created=created)


def ensure_domains(
    domains: Iterable[str], workspace: Workspace, *, first_is_primary: bool
) -> list[DomainResult]:
    """Ensure every domain in order; optionally mark the first as primary."""
    unique = list(dict.fromkeys(domains))
    return [
        ensure_domain(domain, workspace, primary=first_is_primary and index == 0)
        for index, domain in enumerate(unique)
    ]
