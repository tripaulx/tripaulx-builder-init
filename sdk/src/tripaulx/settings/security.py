"""Helpers to derive host-based security settings."""

from __future__ import annotations

from collections.abc import Iterable


def allowed_hosts(base_domain: str, *extra: str) -> list[str]:
    """Return ``ALLOWED_HOSTS`` covering the apex and every workspace subdomain.

    A leading dot (``.example.com``) matches the domain and all subdomains,
    which is what workspace-per-subdomain routing needs.
    """
    return list(dict.fromkeys((f".{base_domain}", *extra)))


def https_origins(hosts: Iterable[str]) -> list[str]:
    """Map explicit hosts to ``https://`` origins for CSRF/CORS settings.

    Wildcards (``*``) and empty entries are ignored. A leading-dot host
    (``.example.com``) becomes ``https://*.example.com``, the wildcard syntax
    accepted by ``CSRF_TRUSTED_ORIGINS``.
    """
    origins: set[str] = set()
    for host in hosts:
        if not host or host == "*":
            continue
        name = f"*{host}" if host.startswith(".") else host
        origins.add(f"https://{name}")
    return sorted(origins)
