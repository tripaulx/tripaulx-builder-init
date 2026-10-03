"""OpenAI client on the Responses API.

The Responses API is the endpoint where reasoning models work fully
(``reasoning``, ``verbosity``, strict structured output), and it serves
older models too: one path, no endpoint choice per family. What changes per
family is the parameter set, governed by ``AIModel.supports_reasoning``:

- reasoning: ``reasoning.effort`` and ``text.verbosity``, never
  ``temperature`` (refused), plus an output-token floor per effort;
- no reasoning: ``temperature`` when set.

``store=False`` on every call: the API keeps conversations by default, and
workspace content has no reason to stay at the provider. No user identifier
is sent. Web search is the ``web_search`` tool, with ``allowed_domains`` when
the agent restricts the sites; sources come back as ``url_citation``
annotations and each ``web_search_call`` is a billed search.
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


class OpenAIClient(ProviderClient):
    """Calls ``client.responses.create`` of the ``openai`` SDK."""

    name = "openai"
    label = "OpenAI"
    extra = "openai"

    def build_params(self, request: AIRequest) -> dict[str, Any]:
        """Return the ``responses.create`` keyword arguments."""
        params: dict[str, Any] = {
            "model": request.model.identifier,
            "instructions": request.instructions,
            "input": request.input,
            "max_output_tokens": output_limit(request),
            "store": False,
        }
        text: dict[str, Any] = {}
        if getattr(request.model, "supports_reasoning", False):
            effort = effective_effort(request)
            if effort:
                params["reasoning"] = {"effort": effort}
            if request.verbosity:
                text["verbosity"] = request.verbosity
        elif request.temperature is not None:
            params["temperature"] = float(request.temperature)
        if request.web_search:
            tool: dict[str, Any] = {"type": "web_search"}
            if request.search_domains:
                tool["filters"] = {"allowed_domains": list(request.search_domains)}
            params["tools"] = [tool]
        if request.output_schema:
            text["format"] = {
                "type": "json_schema",
                "name": (request.schema_name or "answer")[:64],
                "schema": request.output_schema,
                "strict": True,
            }
        if text:
            params["text"] = text
        return params

    def send(self, api_key: str, params: dict[str, Any], timeout_s: float) -> Any:
        """POST to the Responses API (the SDK is imported only here)."""
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderNotInstalled("openai") from exc
        client = OpenAI(api_key=api_key, timeout=timeout_s, max_retries=1)
        return client.responses.create(**params)

    def parse(self, raw: Any, request: AIRequest, *, latency_ms: int) -> AIResponse:
        """Read text, usage, sources and the incomplete reason."""
        usage = getattr(raw, "usage", None)
        input_details = getattr(usage, "input_tokens_details", None)
        output_details = getattr(usage, "output_tokens_details", None)
        sources, searches = (
            _read_search(raw, request.search_domains) if request.web_search else ((), 0)
        )
        incomplete = getattr(raw, "incomplete_details", None)
        return self.finish(
            request,
            text=getattr(raw, "output_text", "") or "",
            incomplete_reason=str(getattr(incomplete, "reason", "") or "")
            if incomplete
            else "",
            response_id=str(getattr(raw, "id", "") or ""),
            responded_model=str(getattr(raw, "model", "") or ""),
            input_tokens=as_int(getattr(usage, "input_tokens", None)),
            output_tokens=as_int(getattr(usage, "output_tokens", None)),
            total_tokens=as_int(getattr(usage, "total_tokens", None)),
            cached_tokens=as_int(getattr(input_details, "cached_tokens", None)) or 0,
            reasoning_tokens=as_int(getattr(output_details, "reasoning_tokens", None))
            or 0,
            latency_ms=latency_ms,
            raw=raw_as_dict(raw),
            sources=sources,
            web_searches=searches,
        )

    def classify_sdk_error(self, exc: BaseException, request: AIRequest) -> AIError:
        """Timeout before connection (it is a subclass), then HTTP status."""
        try:
            import openai
        except ImportError:
            return make("unexpected_error", detail=detail_of(exc))

        if isinstance(exc, openai.APITimeoutError):
            return make(
                "timeout",
                detail=detail_of(exc),
                provider=self.label,
                seconds=int(request.timeout_s),
            )
        if isinstance(exc, openai.APIConnectionError):
            return make("no_connection", detail=detail_of(exc), provider=self.label)
        if isinstance(exc, openai.APIStatusError):
            status = int(getattr(exc, "status_code", 0) or 0)
            return self.error_for_status(status, exc, request)
        return make("unexpected_error", detail=detail_of(exc))


def _read_search(raw: Any, domains: tuple[str, ...]) -> tuple[tuple[dict, ...], int]:
    """Cited sources (``url_citation``) and how many searches were made."""
    sources: dict[str, dict] = {}
    searches = 0
    for item in getattr(raw, "output", None) or []:
        kind = getattr(item, "type", "")
        if kind == "web_search_call":
            searches += 1
            continue
        if kind != "message":
            continue
        for part in getattr(item, "content", None) or []:
            for note in getattr(part, "annotations", None) or []:
                if getattr(note, "type", "") == "url_citation":
                    url = str(getattr(note, "url", "") or "")
                    title = str(getattr(note, "title", "") or "")
                    add_source(sources, url, title, domains)
    return tuple(sources.values()), searches
