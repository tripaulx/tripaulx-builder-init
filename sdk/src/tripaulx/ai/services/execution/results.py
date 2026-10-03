"""Value objects of a run: resolved parameters, steps and the final result."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from tripaulx.ai.providers import AIError


@dataclass(frozen=True)
class Params:
    """The parameters of ONE call, already resolved by precedence."""

    model: Any  # AIModel
    effort: str = ""
    verbosity: str = ""
    max_output_tokens: int | None = None
    temperature: Decimal | None = None


@dataclass(frozen=True)
class StepResult:
    """One call of the run (the single step, a specialist or the consolidation)."""

    position: int
    step: str
    agent: Any
    ok: bool
    text: str = ""
    data: dict | None = None
    model_identifier: str = ""
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: Decimal | None = None
    event_id: UUID | None = None
    error: AIError | None = None
    #: Sources cited when the agent searched the web.
    sources: tuple[dict, ...] = ()


@dataclass(frozen=True)
class RunResult:
    """What the caller gets: the final output, the steps and the totals."""

    ok: bool
    execution_id: UUID
    agent: Any
    text: str = ""
    data: dict | None = None
    model_identifier: str = ""
    steps: tuple[StepResult, ...] = field(default_factory=tuple)
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: Decimal | None = None
    cost_unknown: bool = False
    error: AIError | None = None
    #: Sources of the final step (shown next to the text).
    sources: tuple[dict, ...] = ()


def consolidate(
    execution_id: UUID,
    agent: Any,
    steps: list[StepResult],
    *,
    ok: bool,
    error: AIError | None,
) -> RunResult:
    """Sum the steps into the :class:`RunResult`."""
    costs = [s.cost_usd for s in steps if s.ok]
    known = [c for c in costs if c is not None]
    final = steps[-1] if steps else None
    final_ok = bool(final and ok)
    return RunResult(
        ok=ok,
        execution_id=execution_id,
        agent=agent,
        text=final.text if final_ok else "",
        data=final.data if final_ok else None,
        model_identifier=final.model_identifier if final else "",
        steps=tuple(steps),
        latency_ms=sum(s.latency_ms for s in steps),
        input_tokens=sum(s.input_tokens for s in steps),
        output_tokens=sum(s.output_tokens for s in steps),
        total_tokens=sum(s.total_tokens for s in steps),
        cost_usd=sum(known, Decimal(0)) if known else None,
        cost_unknown=any(c is None for c in costs),
        error=error,
        sources=final.sources if final_ok else (),
    )
