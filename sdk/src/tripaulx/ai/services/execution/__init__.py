"""The runtime: run an agent (alone or with its team) and record every call.

The single entry point for every consumer is :func:`run`. It returns a
:class:`RunResult` and NEVER raises: every failure (configuration, provider,
format) becomes ``ok=False`` with a typed :class:`AIError`, because the UI
wants the diagnosis, and a 500 would blame the app for what the provider
refused.

Alone: one call (``step=single``). Team: the coordinator's specialists run IN
SEQUENCE, each receiving the original input plus a brief of what the
previous ones produced; then the coordinator consolidates. All calls share
``execution_id``. The run stops at the first error: a consolidation over a
silent gap would look complete, and provider errors tend to repeat.

Precedence: skill > agent > settings, field by field (only published skills
take part). Deadline: each call gets ``min(AI_TIMEOUT_S, remaining)`` of
``AI_RUN_DEADLINE_S``, so a team run ends (or fails with ``timeout``) before
the web server kills the worker.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID, uuid4

from tripaulx.ai import providers
from tripaulx.ai.conf import app_settings
from tripaulx.ai.models import AISettings, ExecutionStep
from tripaulx.ai.providers import AIError
from tripaulx.ai.providers.errors import key_complaint, make

from .. import budget, events
from .params import brief
from .results import Params, RunResult, StepResult, consolidate
from .steps import RunContext, run_member

__all__ = ["Params", "RunResult", "StepResult", "run"]


def _precheck(settings: AISettings, agent: Any, text: str) -> AIError | None:
    """Failures found before anything is sent to a provider."""
    label = providers.label_of(settings.provider)
    if not (text or "").strip():
        return make("empty_input")
    if not settings.enabled:
        return make("ai_disabled")
    if providers.get_provider(settings.provider) is None:
        return make("provider_missing", provider=label, extra="ai")
    if not settings.api_key_configured:
        return make("no_key", provider=label)
    complaint = key_complaint(settings.api_key)
    if complaint is not None:
        return AIError("invalid_key", complaint)
    if not agent.active:
        return make("agent_inactive", name=agent.name)
    return budget.check(settings)


def run(
    agent: Any,
    text: str,
    *,
    origin: str,
    reference: str = "",
    user: Any = None,
    context: str = "",
    overlay: str = "",
    execution_id: UUID | str | None = None,
    store_content: bool = True,
) -> RunResult:
    """Run ``agent`` on ``text`` and record everything. Never raises.

    ``store_content=False`` keeps only metrics on this run's events, even
    when the settings store content.
    """
    execution_id = UUID(str(execution_id)) if execution_id else uuid4()
    settings = AISettings.load()
    base = {
        "execution_id": execution_id,
        "origin": origin,
        "reference": reference,
        "user": user,
        "store_content": store_content,
    }
    start = time.monotonic()
    deadline = float(app_settings.AI_RUN_DEADLINE_S)

    def remaining() -> float:
        return deadline - (time.monotonic() - start)

    def fail(error: AIError) -> RunResult:
        ctx = events.EventContext(agent=agent, **base)
        events.record_failure(
            error, ctx, model=settings.model, provider=settings.provider
        )
        return consolidate(execution_id, agent, [], ok=False, error=error)

    error = _precheck(settings, agent, text)
    if error is not None:
        return fail(error)
    shared = RunContext(
        settings=settings,
        client=providers.get_provider(settings.provider),
        base=base,
        context=context or "",
        overlay=overlay or "",
    )
    steps: list[StepResult] = []
    if agent.is_coordinator:
        members = list(agent.live_members())
        if not members:
            return fail(make("empty_team", name=agent.name))
        for position, member in enumerate(members, start=1):
            step = run_member(
                member.specialist,
                text,
                shared,
                step=ExecutionStep.SPECIALIST,
                position=position,
                brief=brief(steps),
                remaining_s=remaining(),
            )
            steps.append(step)
            if not step.ok:
                return consolidate(
                    execution_id, agent, steps, ok=False, error=step.error
                )
        final = run_member(
            agent,
            text,
            shared,
            step=ExecutionStep.CONSOLIDATION,
            position=len(members) + 1,
            brief=brief(steps),
            remaining_s=remaining(),
        )
    else:
        final = run_member(
            agent,
            text,
            shared,
            step=ExecutionStep.SINGLE,
            position=0,
            brief="",
            remaining_s=remaining(),
        )
    steps.append(final)
    return consolidate(execution_id, agent, steps, ok=final.ok, error=final.error)
