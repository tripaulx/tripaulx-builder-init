"""Recording :class:`AIEvent` rows: one per call, on success and on error.

Called by the runtime on both branches, which is what makes the report's
success rate real. Failures that happen BEFORE reaching the provider (AI
off, no key, cap) are recorded too: the report answers "why did AI not
run", not only "how much did it cost".

Labels (agent, user, model) are frozen here. Content (prompt, input, output,
raw) is stored only when ``AISettings.store_content`` is on AND the call did
not opt out (``EventContext.store_content=False``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from tripaulx.ai.models import AIEvent, EventStatus, ExecutionStep
from tripaulx.ai.providers import AIError, AIRequest, AIResponse

from . import prices
from .keys import actor_label


@dataclass(frozen=True)
class EventContext:
    """Where the call came from and who made it."""

    execution_id: UUID
    origin: str
    reference: str = ""
    user: Any = None
    agent: Any = None
    skills: list[dict] = field(default_factory=list)
    step: str = ExecutionStep.SINGLE
    position: int = 0
    operation: str = "run"
    #: ``False`` keeps only metrics, whatever the settings say.
    store_content: bool = True


def _base(ctx: EventContext, *, model: Any, provider: str) -> dict[str, Any]:
    user = ctx.user if getattr(ctx.user, "pk", None) else None
    agent = ctx.agent if getattr(ctx.agent, "pk", None) else None
    return {
        "execution_id": ctx.execution_id,
        "step": ctx.step,
        "position": ctx.position,
        "origin": ctx.origin,
        "reference": (ctx.reference or "")[:120],
        "operation": ctx.operation,
        "agent": agent,
        "agent_label": (agent.name if agent else "")[:80],
        "skills": list(ctx.skills or []),
        "provider": getattr(model, "provider", "") or provider,
        "model_identifier": (getattr(model, "identifier", "") or "")[:120],
        "user": user,
        "user_label": actor_label(user),
    }


def _cost(response: AIResponse, model: Any) -> Decimal | None:
    """Tokens at the model price plus each web search, billed apart.

    No tokens (error before generating) means no cost, not zero. No model
    price means ``None`` even with searches: half a number is worse.
    """
    if not (response.input_tokens or response.output_tokens):
        return None
    cost = prices.cost_usd(
        model,
        response.input_tokens,
        response.output_tokens,
        cached_tokens=response.cached_tokens,
    )
    if cost is None or not response.web_searches:
        return cost
    return cost + prices.web_search_price() * response.web_searches


def record(
    response: AIResponse, request: AIRequest, ctx: EventContext, *, settings: Any
) -> AIEvent:
    """Store the event of a call that was made (successful or not)."""
    model = request.model
    model_prices = prices.prices_for(model)
    fields = _base(ctx, model=model, provider=getattr(settings, "provider", ""))
    fields.update(
        status=EventStatus.SUCCESS if response.ok else EventStatus.ERROR,
        http_status=response.http_status,
        latency_ms=response.latency_ms or None,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        total_tokens=response.total_tokens,
        cached_tokens=response.cached_tokens or None,
        reasoning_tokens=response.reasoning_tokens or None,
        responded_model=(response.responded_model or "")[:120],
        web_searches=response.web_searches or 0,
        cost_usd=_cost(response, model),
        input_price_usd_1m=model_prices.input if model_prices else None,
        output_price_usd_1m=model_prices.output if model_prices else None,
    )
    if response.error is not None:
        # The detail of invalid_json is a piece of the model OUTPUT.
        keep_detail = ctx.store_content or response.error.code != "invalid_json"
        fields.update(
            error_code=response.error.code[:40],
            error_message=response.error.message,
            error_detail=response.error.detail if keep_detail else "",
        )
    if ctx.store_content and getattr(settings, "store_content", True):
        fields.update(
            system_prompt=request.instructions,
            input_text=request.input,
            output_text=response.text,
            raw_response=response.raw or None,
        )
    return AIEvent.objects.create(**fields)


def record_failure(
    error: AIError, ctx: EventContext, *, model: Any = None, provider: str = ""
) -> AIEvent:
    """Store the failure that prevented the call (nothing reached a provider)."""
    fields = _base(ctx, model=model, provider=provider)
    fields.update(
        status=EventStatus.ERROR,
        http_status=None,
        error_code=error.code[:40],
        error_message=error.message,
        error_detail=error.detail,
    )
    return AIEvent.objects.create(**fields)
