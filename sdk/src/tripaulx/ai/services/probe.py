"""The "test AI" call: one real call to the provider, on demand.

Why a real call and not a key check: "configured" only means "the fields
have text". A revoked key, an account without credits, a retired model and a
mistyped identifier all look fine until the first call. This service is that
first call, through the SAME client the runtime uses, so it proves agents
will work with this key and this model.

The result is never an exception: a provider refusal IS the answer the user
asked for. The call is recorded as an event with origin ``test``. The key
never appears in the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from tripaulx.ai import providers
from tripaulx.ai.conf import app_settings
from tripaulx.ai.providers import AIRequest
from tripaulx.ai.providers.errors import key_complaint, make

from . import events, origins

#: Short on purpose: each click spends tokens.
QUESTION = "Answer with the single word: ok"
INSTRUCTIONS = "You are the connection test of an AI integration. Answer exactly."


@dataclass(frozen=True)
class ProbeResult:
    """What the UI shows after "Test"."""

    ok: bool
    #: Round trip in milliseconds, on both outcomes: on an error it tells
    #: "refused at once" from "waited and gave up".
    latency_ms: int
    #: The model the provider says answered (aliases reveal their target).
    model: str = ""
    #: The text returned, cut: proof that generation happened.
    answer: str = ""
    #: The sentence the UI shows; empty when ``ok``.
    error: str = ""
    #: The provider's technical text, for whoever investigates.
    detail: str = ""


def probe(
    settings: Any, *, user: Any = None, timeout: float | None = None
) -> ProbeResult:
    """Call the provider with the stored key and model and report the outcome.

    It does not require AI to be ENABLED: testing before turning it on is
    the natural order. It assumes a key and a model; the view checks that.
    """
    complaint = key_complaint(settings.api_key)
    if complaint is not None:
        return ProbeResult(ok=False, latency_ms=0, error=complaint)
    client = providers.get_provider(settings.provider)
    if client is None:
        error = make("provider_missing", provider=settings.provider, extra="ai")
        return ProbeResult(ok=False, latency_ms=0, error=error.message)
    model = settings.model
    request = AIRequest(
        model=model,
        instructions=INSTRUCTIONS,
        input=QUESTION,
        api_key=settings.api_key,
        timeout_s=float(timeout or app_settings.AI_TEST_TIMEOUT_S),
    )
    response = client.call(request)
    events.record(
        response,
        request,
        events.EventContext(
            execution_id=uuid4(), origin=origins.TEST, user=user, operation="test"
        ),
        settings=settings,
    )
    if response.ok:
        return ProbeResult(
            ok=True,
            latency_ms=response.latency_ms,
            model=response.responded_model or model.identifier,
            answer=response.text[:200],
        )
    error = response.error
    return ProbeResult(
        ok=False,
        latency_ms=response.latency_ms,
        model=response.responded_model,
        error=error.message if error else "",
        detail=error.detail if error else "",
    )
