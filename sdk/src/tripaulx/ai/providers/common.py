"""Pure helpers shared by the provider clients (no network, no SDK)."""

from __future__ import annotations

import json
from typing import Any

from tripaulx.ai.conf import app_settings

#: Output-token floor per reasoning effort: reasoning eats this budget BEFORE
#: the text, and a low ceiling returns an empty, "incomplete" answer.
OUTPUT_FLOOR_BY_EFFORT: dict[str, int] = {
    "minimal": 2000,
    "low": 4000,
    "medium": 8000,
    "high": 16000,
}
#: Effort assumed for the floor when no level defined one.
PROVIDER_DEFAULT_EFFORT = "medium"
#: Output limit of models without reasoning when nobody set one.
DEFAULT_OUTPUT_WITHOUT_REASONING = 4000


def effective_effort(request: Any) -> str:
    """Return the effort to send: "minimal" becomes "low" where refused.

    Web search refuses "minimal", and so do models with
    ``accepts_minimal_effort=False``. An agent set to "minimal" keeps working
    when it switches models instead of every call failing with a 400.
    """
    if request.effort == "minimal" and (
        request.web_search or not getattr(request.model, "accepts_minimal_effort", True)
    ):
        return "low"
    return request.effort


def output_limit(request: Any) -> int:
    """Effective output limit: request vs. effort floor, within the hard cap."""
    ceiling = int(app_settings.AI_MAX_OUTPUT_TOKENS)
    if getattr(request.model, "supports_reasoning", False):
        effort = effective_effort(request) or PROVIDER_DEFAULT_EFFORT
        floor = OUTPUT_FLOOR_BY_EFFORT.get(effort, OUTPUT_FLOOR_BY_EFFORT["medium"])
        return min(max(request.max_output_tokens or 0, floor), ceiling)
    return min(request.max_output_tokens or DEFAULT_OUTPUT_WITHOUT_REASONING, ceiling)


def as_int(value: Any) -> int | None:
    """``int(value)``, or ``None`` when it is missing or not a number."""
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def detail_of(exc: BaseException) -> str:
    """Return the provider text inside an SDK exception, or ``str(exc)``."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        inner = body.get("error")
        if isinstance(inner, dict) and isinstance(inner.get("message"), str):
            return inner["message"].strip()[:2000]
        if isinstance(body.get("message"), str):
            return body["message"].strip()[:2000]
    return str(exc)[:2000]


def in_domains(url: str, domains: tuple[str, ...]) -> bool:
    """Whether the host of ``url`` is one of ``domains`` or a subdomain."""
    host = url.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower()
    return any(host == d or host.endswith(f".{d}") for d in domains)


def add_source(
    sources: dict[str, dict], url: str, title: str, domains: tuple[str, ...]
) -> None:
    """Add a cited source once; skip non-HTTPS and off-domain links.

    The provider filter already restricts the domains; this is the second
    lock, so a link from another site is never offered as a source.
    """
    if not url.startswith("https://") or url in sources:
        return
    if domains and not in_domains(url, domains):
        return
    sources[url] = {"url": url, "title": (title.strip() or url)[:300]}


def raw_as_dict(raw: Any) -> dict:
    """Return the SDK response as a JSON dict (empty on failure)."""
    dump = getattr(raw, "model_dump", None)
    if not callable(dump):
        return {}
    try:
        return dump(mode="json")
    except TypeError:
        return dump()
    except Exception:  # noqa: BLE001 - diagnosis only, never breaks the call
        return {}


def parse_json_object(text: str) -> dict | None:
    """``json.loads(text)`` when it is an object, else ``None``."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None
