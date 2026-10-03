"""The provider interface: ``AIRequest`` in, ``AIResponse`` out, never raising.

:meth:`ProviderClient.call` is a template method shared by every provider:
check the key, build the parameters, send them (the network seam tests
replace), then parse the answer. Any failure becomes ``AIResponse(ok=False,
error=AIError)``: the caller records the event and shows the diagnosis, it
does not answer with a 500.

Subclasses implement four steps: :meth:`build_params` (pure, no network),
:meth:`send` (the SDK call, importing the SDK lazily), :meth:`parse` and
:meth:`classify_sdk_error`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
import logging
import time
from typing import Any

from . import errors
from .common import detail_of, parse_json_object
from .errors import AIError

logger = logging.getLogger("tripaulx.ai")


class ProviderNotInstalled(ImportError):
    """The SDK of a provider is not installed (missing optional extra)."""


@dataclass(frozen=True)
class AIRequest:
    """Everything one call needs, already resolved (nothing left to inherit)."""

    model: Any  # tripaulx.ai.catalog.models.AIModel
    instructions: str
    input: str
    api_key: str
    effort: str = ""
    verbosity: str = ""
    max_output_tokens: int | None = None
    temperature: Decimal | None = None
    output_schema: dict | None = None
    schema_name: str = "answer"
    timeout_s: float = 120.0
    #: May search the web; empty ``search_domains`` means any site.
    web_search: bool = False
    search_domains: tuple[str, ...] = ()


@dataclass(frozen=True)
class AIResponse:
    """What came back (or what failed), normalized across providers."""

    ok: bool
    text: str = ""
    data: dict | None = None
    response_id: str = ""
    responded_model: str = ""
    #: Input tokens INCLUDING the cached ones.
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    latency_ms: int = 0
    http_status: int | None = None
    incomplete_reason: str = ""
    raw: dict = field(default_factory=dict)
    error: AIError | None = None
    #: Sources cited by web search (``{"url", "title"}``), without repeats.
    sources: tuple[dict, ...] = ()
    #: How many web searches the model made (each one is billed).
    web_searches: int = 0


class ProviderClient(ABC):
    """Base class of a provider client; subclasses set ``name`` and ``label``."""

    name: str = ""
    label: str = ""
    #: The ``tripaulx-sdk[...]`` extra that installs the provider SDK.
    extra: str = ""

    def call(self, request: AIRequest) -> AIResponse:
        """Make the call and return an :class:`AIResponse`. Never raises."""
        complaint = errors.key_complaint(request.api_key)
        if complaint is not None:
            return AIResponse(ok=False, error=AIError("invalid_key", complaint))
        start = time.monotonic()

        def elapsed() -> int:
            return int((time.monotonic() - start) * 1000)

        try:
            params = self.build_params(request)
            raw = self.send(request.api_key, params, request.timeout_s)
        except Exception as exc:  # noqa: BLE001 - every failure is a diagnosis
            error = self.classify_error(exc, request)
            return AIResponse(
                ok=False,
                error=error,
                http_status=error.http_status,
                latency_ms=elapsed(),
            )
        try:
            return self.parse(raw, request, latency_ms=elapsed())
        except Exception as exc:  # noqa: BLE001 - a parsing bug is not a 500
            logger.exception("Could not parse the %s response", self.name)
            return AIResponse(
                ok=False,
                latency_ms=elapsed(),
                error=errors.make("unexpected_error", detail=str(exc)[:2000]),
            )

    def classify_error(self, exc: BaseException, request: AIRequest) -> AIError:
        """Turn any exception of :meth:`send` into the right :class:`AIError`."""
        if isinstance(exc, UnicodeEncodeError):
            complaint = errors.key_complaint(str(exc.object))
            fallback = str(errors.MESSAGES["unexpected_error"])
            return AIError("invalid_key", complaint or fallback)
        if isinstance(exc, ProviderNotInstalled):
            return errors.make(
                "provider_missing",
                detail=str(exc),
                provider=self.label,
                extra=self.extra,
            )
        return self.classify_sdk_error(exc, request)

    def error_for_status(
        self, status: int, exc: BaseException, request: AIRequest
    ) -> AIError:
        """Return the :class:`AIError` for an HTTP status of the provider."""
        return errors.make(
            errors.code_for_status(status),
            http_status=status,
            detail=detail_of(exc),
            provider=self.label,
            model=getattr(request.model, "identifier", ""),
        )

    def finish(
        self,
        request: AIRequest,
        *,
        text: str,
        incomplete_reason: str = "",
        refused: bool = False,
        **fields: Any,
    ) -> AIResponse:
        """Build the final response: incomplete, refused, JSON check, success."""
        fields.setdefault("http_status", 200)
        if refused:
            error = errors.make("refused", http_status=200, detail=incomplete_reason)
            return AIResponse(ok=False, text=text, error=error, **fields)
        if incomplete_reason:
            error = errors.make(
                "incomplete_response", http_status=200, detail=incomplete_reason
            )
            return AIResponse(
                ok=False,
                text=text,
                incomplete_reason=incomplete_reason,
                error=error,
                **fields,
            )
        data = None
        if request.output_schema:
            data = parse_json_object(text)
            if data is None:
                error = errors.make("invalid_json", http_status=200, detail=text[:500])
                return AIResponse(ok=False, text=text, error=error, **fields)
        return AIResponse(ok=True, text=text, data=data, **fields)

    @abstractmethod
    def build_params(self, request: AIRequest) -> dict[str, Any]:
        """Return the SDK keyword arguments (pure, no network)."""

    @abstractmethod
    def send(self, api_key: str, params: dict[str, Any], timeout_s: float) -> Any:
        """Call the provider SDK. The network seam tests replace."""

    @abstractmethod
    def parse(self, raw: Any, request: AIRequest, *, latency_ms: int) -> AIResponse:
        """Normalize the SDK response into an :class:`AIResponse`."""

    @abstractmethod
    def classify_sdk_error(self, exc: BaseException, request: AIRequest) -> AIError:
        """Map an SDK exception (timeout, connection, status) to an error."""
