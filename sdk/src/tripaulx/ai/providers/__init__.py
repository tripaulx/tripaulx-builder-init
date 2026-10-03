"""Provider registry: which :class:`ProviderClient` answers for a name.

Resolution order for a name: clients registered at runtime with
:func:`register`, then ``TRIPAULX["AI_PROVIDERS"]`` (name -> dotted path),
then the built-in OpenAI and Anthropic clients. Their SDKs are optional
extras (``tripaulx-sdk[openai]``, ``[anthropic]`` or ``[ai]``) and are
imported only when a call is made; a missing SDK becomes the
``provider_missing`` error, never an ``ImportError`` at startup.

Adding a provider::

    from tripaulx.ai import providers

    providers.register("acme", AcmeClient())  # or a class or a dotted path
"""

from __future__ import annotations

from django.utils.module_loading import import_string

from tripaulx.ai.conf import app_settings

from .base import AIRequest, AIResponse, ProviderClient, ProviderNotInstalled
from .errors import AIError

BUILTIN_PROVIDERS: dict[str, str] = {
    "openai": "tripaulx.ai.providers.openai_responses.OpenAIClient",
    "anthropic": "tripaulx.ai.providers.anthropic_messages.AnthropicClient",
}

_registered: dict[str, ProviderClient | type | str] = {}


def register(name: str, client: ProviderClient | type | str) -> None:
    """Register ``client`` (instance, class or dotted path) under ``name``."""
    _registered[name] = client


def unregister(name: str) -> None:
    """Remove a runtime registration (settings and built-ins stay)."""
    _registered.pop(name, None)


def _sources() -> dict[str, ProviderClient | type | str]:
    """Every known name with its client spec, by precedence."""
    merged: dict[str, ProviderClient | type | str] = dict(BUILTIN_PROVIDERS)
    merged.update(app_settings.AI_PROVIDERS or {})
    merged.update(_registered)
    return merged


def _instantiate(spec: ProviderClient | type | str) -> ProviderClient:
    """Turn a client spec into an instance."""
    if isinstance(spec, str):
        spec = import_string(spec)
    return spec() if isinstance(spec, type) else spec


def get_provider(name: str) -> ProviderClient | None:
    """Return the client registered for ``name``, or ``None``."""
    spec = _sources().get(name or "")
    return _instantiate(spec) if spec is not None else None


def names() -> list[str]:
    """Every registered provider name, built-ins first."""
    return list(_sources())


def choices() -> list[tuple[str, str]]:
    """``(name, label)`` of every provider, for selects and validation."""
    return [(name, get_provider(name).label or name) for name in names()]


def label_of(name: str) -> str:
    """Display label of ``name`` (the name itself when unknown)."""
    client = get_provider(name)
    return (client.label or name) if client is not None else name


__all__ = [
    "AIError",
    "AIRequest",
    "AIResponse",
    "BUILTIN_PROVIDERS",
    "ProviderClient",
    "ProviderNotInstalled",
    "choices",
    "get_provider",
    "label_of",
    "names",
    "register",
    "unregister",
]
