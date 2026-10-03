"""The AI dashboard: settings state, budget, counts and today's/30-day usage."""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Q, QuerySet, Sum
from django.utils import timezone

from tripaulx.ai import providers
from tripaulx.ai.models import Agent, AgentRole, AIEvent, AISettings, Skill

from . import budget
from .report import NO_PRICE, events_between, period, recent


def _short(qs: QuerySet) -> dict[str, Any]:
    t = qs.aggregate(
        calls=Count("id"),
        runs=Count("execution_id", distinct=True),
        errors=Count("id", filter=Q(status="error")),
        cost=Sum("cost_usd"),
    )
    return {
        "calls": t["calls"] or 0,
        "runs": t["runs"] or 0,
        "errors": t["errors"] or 0,
        "cost_usd": float(t["cost"] or 0),
    }


def _settings_state(settings: AISettings) -> dict[str, Any]:
    model = settings.model
    return {
        "enabled": settings.enabled,
        "ready": settings.ready,
        "provider": settings.provider,
        "provider_label": providers.label_of(settings.provider),
        "model": settings.model_identifier,
        "model_label": model.label if model else "",
        "api_key_configured": settings.api_key_configured,
        "daily_cap_usd": float(settings.daily_cap_usd)
        if settings.daily_cap_usd is not None
        else None,
        "store_content": settings.store_content,
        "retention_days": settings.retention_days,
    }


def dashboard() -> dict[str, Any]:
    """Every number of the AI hub in one call (events are model rows)."""
    settings = AISettings.load()
    today = timezone.localdate()
    start30, _end = period(30)
    last30 = events_between(start30, today)
    agents = Agent.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(active=True)),
        coordinators=Count("id", filter=Q(role=AgentRole.COORDINATOR)),
        specialists=Count("id", filter=Q(role=AgentRole.SPECIALIST)),
    )
    skills = Skill.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(active=True)),
        published=Count("id", filter=Q(published_version__isnull=False)),
    )
    pending = sum(
        1
        for s in Skill.objects.select_related("published_version")
        if s.has_pending_draft
    )
    return {
        "settings": _settings_state(settings),
        "budget": budget.summary(settings),
        "agents": {k: v or 0 for k, v in agents.items()},
        "skills": {**{k: v or 0 for k, v in skills.items()}, "pending_draft": pending},
        "today": _short(events_between(today, today)),
        "last_30_days": {**_short(last30), "no_price": last30.filter(NO_PRICE).count()},
        "last_event": AIEvent.objects.select_related("agent").first(),
        "recent": recent(5),
    }
