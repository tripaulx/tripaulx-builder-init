"""Anthropic client on the Messages API.

Parameters per model family (``AIModel`` flags and ``options``):

- current models (``supports_reasoning``): thinking is adaptive and always
  on; depth is ``output_config.effort`` (low/medium/high; "minimal" is sent
  as "low"). Sampling parameters are never sent: these models refuse them.
- older models (``uses_thinking_budget``): the effort becomes a thinking
  token budget (``thinking.budget_tokens``), always below ``max_tokens``.
- models without reasoning: ``temperature`` when set.

Strict JSON uses ``output_config.format`` (a JSON schema), not a forced tool:
current models refuse forced ``tool_choice``. Web search is the server tool
(``options["web_search_tool"]`` picks the version, default
``web_search_20260209``) with ``allowed_domains``; sources come from
``web_search_result_location`` citations and the count from
``usage.server_tool_use``. ``options["fallbacks"]`` (e.g. ``"default"``)
turns on server-side refusal fallbacks through the beta endpoint.

Usage mapping: Anthropic reports uncached input apart from cache reads and
writes; ``input_tokens`` here is their sum, ``cached_tokens`` the reads.
"""

from __future__ import annotations

from typing import Any

from .base import AIRequest, AIResponse, ProviderClient, ProviderNotInstalled
from .common import (
    add_source,
    as_int,
    detail_of,
    effective_effort,
    output_limit,
    raw_as_dict,
)
from .errors import AIError, make

#: Thinking budget per effort, for models that take a budget.
THINKING_BUDGET = {"minimal": 1024, "low": 2048, "medium": 4096, "high": 8192}
MIN_THINKING_BUDGET = 1024
DEFAULT_WEB_SEARCH_TOOL = "web_search_20260209"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
INCOMPLETE_STOPS = frozenset(
    {"max_tokens", "model_context_window_exceeded", "pause_turn"}
)


class AnthropicClient(ProviderClient):
    """Calls ``client.messages.create`` of the ``anthropic`` SDK."""

    name = "anthropic"
    label = "Anthropic"
    extra = "anthropic"

    def build_params(self, request: AIRequest) -> dict[str, Any]:
        """Return the ``messages.create`` keyword arguments."""
        model = request.model
        options = getattr(model, "options", None) or {}
        max_tokens = output_limit(request)
        params: dict[str, Any] = {
            "model": model.identifier,
            "max_tokens": max_tokens,
            "system": request.instructions,
            "messages": [{"role": "user", "content": request.input}],
        }
        config: dict[str, Any] = {}
        effort = effective_effort(request)
        if getattr(model, "uses_thinking_budget", False):
            budget = min(
                THINKING_BUDGET.get(effort, 0), max_tokens - MIN_THINKING_BUDGET
            )
            if effort and budget >= MIN_THINKING_BUDGET:
                params["thinking"] = {"type": "enabled", "budget_tokens": budget}
        elif getattr(model, "supports_reasoning", False):
            if effort:
                config["effort"] = "low" if effort == "minimal" else effort
        elif request.temperature is not None:
            params["extra_body"] = {"temperature": float(request.temperature)}
        if request.output_schema:
            config["format"] = {"type": "json_schema", "schema": request.output_schema}
        if config:
            params["output_config"] = config
        if request.web_search:
            tool: dict[str, Any] = {
                "type": options.get("web_search_tool") or DEFAULT_WEB_SEARCH_TOOL,
                "name": "web_search",
                "max_uses": int(options.get("web_search_max_uses") or 5),
            }
            if request.search_domains:
                tool["allowed_domains"] = list(request.search_domains)
            params["tools"] = [tool]
        if options.get("fallbacks"):
            params["fallbacks"] = options["fallbacks"]
            params["betas"] = [FALLBACK_BETA]
        return params

    def send(self, api_key: str, params: dict[str, Any], timeout_s: float) -> Any:
        """POST to the Messages API (the SDK is imported only here)."""
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ProviderNotInstalled("anthropic") from exc
        client = Anthropic(api_key=api_key, timeout=timeout_s, max_retries=1)
        if "betas" in params:
            return client.beta.messages.create(**params)
        return client.messages.create(**params)

    def parse(self, raw: Any, request: AIRequest, *, latency_ms: int) -> AIResponse:
        """Read text blocks, citations, usage and the stop reason."""
        texts: list[str] = []
        sources: dict[str, dict] = {}
        for block in getattr(raw, "content", None) or []:
            if getattr(block, "type", "") != "text":
                continue
            texts.append(getattr(block, "text", "") or "")
            for cite in getattr(block, "citations", None) or []:
                if getattr(cite, "type", "") == "web_search_result_location":
                    url = str(getattr(cite, "url", "") or "")
                    title = str(getattr(cite, "title", "") or "")
                    add_source(sources, url, title, request.search_domains)
        usage = getattr(raw, "usage", None)
        uncached = as_int(getattr(usage, "input_tokens", None))
        read = as_int(getattr(usage, "cache_read_input_tokens", None)) or 0
        written = as_int(getattr(usage, "cache_creation_input_tokens", None)) or 0
        output = as_int(getattr(usage, "output_tokens", None))
        total_input = None if uncached is None else uncached + read + written
        details = getattr(usage, "output_tokens_details", None)
        server = getattr(usage, "server_tool_use", None)
        stop = str(getattr(raw, "stop_reason", "") or "")
        return self.finish(
            request,
            text="".join(texts),
            refused=stop == "refusal",
            incomplete_reason=_stop_detail(stop, getattr(raw, "stop_details", None)),
            response_id=str(getattr(raw, "id", "") or ""),
            responded_model=str(getattr(raw, "model", "") or ""),
            input_tokens=total_input,
            output_tokens=output,
            total_tokens=None
            if total_input is None and output is None
            else (total_input or 0) + (output or 0),
            cached_tokens=read,
            reasoning_tokens=as_int(getattr(details, "thinking_tokens", None)) or 0,
            latency_ms=latency_ms,
            raw=raw_as_dict(raw),
            sources=tuple(sources.values()),
            web_searches=as_int(getattr(server, "web_search_requests", None)) or 0,
        )

    def classify_sdk_error(self, exc: BaseException, request: AIRequest) -> AIError:
        """Timeout before connection (it is a subclass), then HTTP status."""
        try:
            import anthropic
        except ImportError:
            return make("unexpected_error", detail=detail_of(exc))
        if isinstance(exc, anthropic.APITimeoutError):
            return make(
                "timeout",
                detail=detail_of(exc),
                provider=self.label,
                seconds=int(request.timeout_s),
            )
        if isinstance(exc, anthropic.APIConnectionError):
            return make("no_connection", detail=detail_of(exc), provider=self.label)
        if isinstance(exc, anthropic.APIStatusError):
            status = int(getattr(exc, "status_code", 0) or 0)
            return self.error_for_status(status, exc, request)
        return make("unexpected_error", detail=detail_of(exc))


def _stop_detail(stop: str, details: Any) -> str:
    """Return the incomplete reason, the refusal category or ``""``."""
    if stop in INCOMPLETE_STOPS:
        return stop
    if stop == "refusal":
        return str(getattr(details, "category", "") or "refusal")
    return ""
