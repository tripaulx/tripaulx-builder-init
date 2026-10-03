"""Relying-party identity and challenge storage for WebAuthn.

**The RP ID and origin come from the request**, not from a constant: a
passkey is bound to a domain, and the browser requires the RP ID to be the
page's own domain or a registrable suffix of it. Each workspace has its own
subdomain, so a fixed value would serve one and break the others.
``WEBAUTHN_RP_ID`` still wins when set (to pin a parent domain), and
``WEBAUTHN_ORIGINS`` adds origins to the request's own.

Challenges are stored in the Django cache between "begin" and "complete".
With more than one worker process, production **must** use a shared cache
(Redis): ``LocMemCache`` is per process, so "complete" could land on a
worker that never saw the challenge.
"""

from __future__ import annotations

from django.core.cache import cache
from django.http import HttpRequest
from django.http.request import split_domain_port

from tripaulx.core.conf import app_settings as core_settings

from ...conf import app_settings

REGISTRATION_PREFIX = "tpsdk:webauthn:reg:"
AUTHENTICATION_PREFIX = "tpsdk:webauthn:auth:"


def rp_id_for(request: HttpRequest) -> str:
    """Return the RP ID: the setting when set, else the host without port.

    ``get_host()`` was already validated against ``ALLOWED_HOSTS``.
    """
    if app_settings.WEBAUTHN_RP_ID:
        return app_settings.WEBAUTHN_RP_ID
    domain, _port = split_domain_port(request.get_host())
    return domain


def rp_name() -> str:
    """Return the RP name shown by the browser (default ``APP_NAME``)."""
    return app_settings.WEBAUTHN_RP_NAME or core_settings.APP_NAME


def expected_origins_for(request: HttpRequest) -> list[str]:
    """Return the accepted origins: the request's own, then the extras."""
    own = f"{request.scheme}://{request.get_host()}"
    extras = [origin for origin in app_settings.WEBAUTHN_ORIGINS if origin != own]
    return [own, *extras]


def store_challenge(key: str, challenge_b64: str) -> None:
    """Keep a challenge until it is used or expires."""
    cache.set(key, challenge_b64, app_settings.WEBAUTHN_CHALLENGE_TTL)


def pop_challenge(key: str) -> str | None:
    """Return and forget a challenge (each one is single-use)."""
    value = cache.get(key)
    cache.delete(key)
    return value
