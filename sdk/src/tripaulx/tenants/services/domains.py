"""Hostnames derived from workspace slugs."""

from __future__ import annotations

from ..conf import app_settings


def workspace_domain(slug: str, base_domain: str | None = None) -> str:
    """Return the subdomain of a workspace, e.g. ``acme-co.example.com``."""
    base = base_domain or app_settings.BASE_DOMAIN
    return f"{slug.replace('_', '-')}.{base}"


def public_domains(base_domain: str | None = None) -> list[str]:
    """Return the hostnames served by the public schema, without duplicates."""
    base = base_domain or app_settings.BASE_DOMAIN
    hosts = (base, f"www.{base}", *app_settings.PUBLIC_DOMAINS)
    return list(dict.fromkeys(hosts))
