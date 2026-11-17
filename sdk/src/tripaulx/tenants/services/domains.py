"""Hostnames derived from workspace slugs."""

from __future__ import annotations

from django.http import HttpRequest
from django.http.request import split_domain_port

from ..conf import app_settings

#: Placeholder of the subdomain label in :func:`workspace_origin_template`.
SUBDOMAIN = "{subdomain}"


def workspace_domain(slug: str, base_domain: str | None = None) -> str:
    """Return the subdomain of a workspace, e.g. ``acme-co.example.com``."""
    base = base_domain or app_settings.BASE_DOMAIN
    return f"{slug.replace('_', '-')}.{base}"


def public_domains(base_domain: str | None = None) -> list[str]:
    """Return the hostnames served by the public schema, without duplicates."""
    base = base_domain or app_settings.BASE_DOMAIN
    hosts = (base, f"www.{base}", *app_settings.PUBLIC_DOMAINS)
    return list(dict.fromkeys(hosts))


def request_origin(request: HttpRequest, host: str) -> str:
    """Return ``scheme://host[:port]`` using the request's scheme and port."""
    _host, port = split_domain_port(request.get_host())
    authority = f"{host}:{port}" if port else host
    return f"{request.scheme}://{authority}"


def workspace_origin(request: HttpRequest, slug: str) -> str:
    """Return the origin of workspace ``slug`` (e.g. ``https://acme.example.com``)."""
    return request_origin(request, workspace_domain(slug))


def workspace_origin_template(request: HttpRequest) -> str:
    """Return the workspace origin with ``{subdomain}`` in place of the label.

    The subdomain is the slug with ``_`` replaced by ``-``.
    """
    return request_origin(request, workspace_domain("x").replace("x", SUBDOMAIN, 1))
