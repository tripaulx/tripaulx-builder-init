"""One complete call for one agent: prompt, provider, event. Never raises."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from tripaulx.ai.conf import app_settings
from tripaulx.ai.providers import AIError, AIRequest, ProviderClient
from tripaulx.ai.providers.errors import make

from .. import events, prompt
from . import params as resolution
from .results import StepResult

logger = logging.getLogger("tripaulx.ai")

#: Below this, starting a call is pointless: fail cleanly with a timeout.
MIN_SECONDS_TO_CALL = 5.0


@dataclass(frozen=True)
class RunContext:
    """What every step of one run shares."""

    settings: Any
    client: ProviderClient
    base: dict[str, Any]
    context: str = ""
    overlay: str = ""


def _failed(
    agent: Any,
    step: str,
    position: int,
    error: AIError,
    ctx: Any,
    run: RunContext,
    *,
    model: Any = None,
) -> StepResult:
    event = events.record_failure(
        error, ctx, model=model, provider=run.settings.provider
    )
    return StepResult(
        position=position,
        step=step,
        agent=agent,
        ok=False,
        model_identifier=getattr(model, "identifier", "") or "",
        event_id=event.id,
        error=error,
    )


def _request(
    target: Any,
    text: str,
    run: RunContext,
    *,
    p: Any,
    skills: list,
    brief: str,
    remaining_s: float,
) -> AIRequest:
    schema = target.output_schema if isinstance(target.output_schema, dict) else None
    schema = schema or None
    return AIRequest(
        model=p.model,
        instructions=prompt.build_instructions(
            target,
            [v for _link, v in skills],
            overlay=run.overlay,
            output_schema=schema,
        ),
        input=prompt.build_input(target, text, context=run.context, brief=brief),
        api_key=run.settings.api_key,
        effort=p.effort,
        verbosity=p.verbosity,
        max_output_tokens=p.max_output_tokens,
        temperature=p.temperature,
        output_schema=schema,
        schema_name=target.slug or "answer",
        timeout_s=min(float(app_settings.AI_TIMEOUT_S), remaining_s),
        web_search=bool(target.web_search),
        search_domains=tuple(target.web_search_domains or ()),
    )


def run_member(
    target: Any,
    text: str,
    run: RunContext,
    *,
    step: str,
    position: int,
    brief: str,
    remaining_s: float,
) -> StepResult:
    """Run ``target`` once and record its event. Never raises."""
    ctx = events.EventContext(agent=target, step=step, position=position, **run.base)
    try:
        skills = resolution.skills_of(target)
        if isinstance(skills, AIError):
            return _failed(target, step, position, skills, ctx, run)
        p = resolution.resolve(run.settings, target, skills)
        if isinstance(p, AIError):
            return _failed(target, step, position, p, ctx, run)
        if remaining_s < MIN_SECONDS_TO_CALL:
            seconds = int(app_settings.AI_RUN_DEADLINE_S)
            error = make("timeout", provider=run.client.label, seconds=seconds)
            return _failed(target, step, position, error, ctx, run, model=p.model)
        ctx = events.EventContext(
            agent=target,
            step=step,
            position=position,
            skills=resolution.skills_for_event(skills),
            **run.base,
        )
        request = _request(
            target, text, run, p=p, skills=skills, brief=brief, remaining_s=remaining_s
        )
        response = run.client.call(request)
        event = events.record(response, request, ctx, settings=run.settings)
        return StepResult(
            position=position,
            step=step,
            agent=target,
            ok=response.ok,
            text=response.text,
            data=response.data,
            model_identifier=p.model.identifier,
            latency_ms=response.latency_ms,
            input_tokens=response.input_tokens or 0,
            output_tokens=response.output_tokens or 0,
            total_tokens=response.total_tokens or 0,
            cost_usd=event.cost_usd,
            event_id=event.id,
            error=response.error,
            sources=response.sources,
        )
    except Exception as exc:  # noqa: BLE001 - the runtime never breaks a request
        logger.exception("Unexpected failure running agent %s", target.slug)
        error = make("unexpected_error", detail=str(exc)[:2000])
        try:
            return _failed(target, step, position, error, ctx, run)
        except Exception:  # noqa: BLE001 - not even recording may break it
            logger.exception("Could not record the failure of agent %s", target.slug)
            return StepResult(
                position=position, step=step, agent=target, ok=False, error=error
            )
