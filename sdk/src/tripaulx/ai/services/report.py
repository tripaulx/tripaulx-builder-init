"""Usage report: totals, breakdowns and the daily series of 7, 30 or 90 days.

Dates are local (``TIME_ZONE``). The series is filled with zeros on days
without events so charts never skip dates. ``no_price`` is a separate query
on purpose: inside ``aggregate`` the ``Sum("cost_usd")`` alias shadows the
field, and a ``cost_usd__isnull`` filter would look at the sum.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db.models import Avg, Count, F, Q, QuerySet, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from tripaulx.ai.models import AIEvent, AISettings, EventStatus
from tripaulx.ai.providers.errors import label as error_label

from . import budget, origins

ALLOWED_DAYS = (7, 30, 90)
SUCCESS = Q(status=EventStatus.SUCCESS)
ERROR = Q(status=EventStatus.ERROR)
NO_PRICE = Q(status=EventStatus.SUCCESS, cost_usd__isnull=True)


def _f(value: Any) -> float:
    return float(value or 0)


def period(days: int) -> tuple[date, date]:
    """First and last local day of the last ``days`` days."""
    end = timezone.localdate()
    return end - timedelta(days=days - 1), end


def events_between(start: date, end: date) -> QuerySet:
    """Events created between two local days (inclusive)."""
    return AIEvent.objects.filter(
        created_at__date__gte=start, created_at__date__lte=end
    )


def totals(qs: QuerySet) -> dict[str, Any]:
    """Sum calls, runs, success rate, tokens, cost and latency of ``qs``."""
    t = qs.aggregate(
        calls=Count("id"),
        success=Count("id", filter=SUCCESS),
        errors=Count("id", filter=ERROR),
        runs=Count("execution_id", distinct=True),
        input_tokens=Sum("input_tokens"),
        output_tokens=Sum("output_tokens"),
        total_tokens=Sum("total_tokens"),
        cost=Sum("cost_usd"),
        latency=Avg("latency_ms", filter=SUCCESS),
    )
    calls = t["calls"] or 0
    return {
        "runs": t["runs"] or 0,
        "calls": calls,
        "success": t["success"] or 0,
        "errors": t["errors"] or 0,
        "success_rate": round(100.0 * (t["success"] or 0) / calls, 1) if calls else 0.0,
        "input_tokens": t["input_tokens"] or 0,
        "output_tokens": t["output_tokens"] or 0,
        "total_tokens": t["total_tokens"] or 0,
        "cost_usd": _f(t["cost"]),
        "no_price": qs.filter(NO_PRICE).count(),
        "avg_latency_ms": int(t["latency"] or 0),
    }


def daily_series(qs: QuerySet, start: date, end: date) -> list[dict[str, Any]]:
    """One row per day (zeros included)."""
    by_day = {
        row["day"]: row
        for row in qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            calls=Count("id"),
            total_tokens=Sum("total_tokens"),
            cost=Sum("cost_usd"),
            errors=Count("id", filter=ERROR),
        )
    }
    series, day = [], start
    while day <= end:
        row = by_day.get(day, {})
        series.append(
            {
                "day": day.isoformat(),
                "calls": row.get("calls", 0) or 0,
                "total_tokens": row.get("total_tokens", 0) or 0,
                "cost_usd": _f(row.get("cost")),
                "errors": row.get("errors", 0) or 0,
            }
        )
        day += timedelta(days=1)
    return series


def _breakdowns(qs: QuerySet) -> dict[str, list[dict[str, Any]]]:
    cost_desc = F("cost").desc(nulls_last=True)
    by_model = qs.values("provider", "model_identifier").annotate(
        calls=Count("id"),
        total_tokens=Sum("total_tokens"),
        cost=Sum("cost_usd"),
        no_price=Count("id", filter=NO_PRICE),
    )
    by_agent = qs.values("agent_id", "agent_label").annotate(
        calls=Count("id"),
        runs=Count("execution_id", distinct=True),
        errors=Count("id", filter=ERROR),
        cost=Sum("cost_usd"),
    )
    by_origin = qs.values("origin").annotate(calls=Count("id"), cost=Sum("cost_usd"))
    by_error = qs.filter(ERROR).values("error_code").annotate(calls=Count("id"))
    return {
        "by_model": [
            {
                "provider": r["provider"],
                "model": r["model_identifier"] or "—",
                "calls": r["calls"],
                "total_tokens": r["total_tokens"] or 0,
                "cost_usd": _f(r["cost"]),
                "no_price": r["no_price"],
            }
            for r in by_model.order_by(cost_desc, "-calls")
        ],
        "by_agent": [
            {
                "agent_id": str(r["agent_id"]) if r["agent_id"] else None,
                "agent": r["agent_label"] or "—",
                "calls": r["calls"],
                "runs": r["runs"],
                "errors": r["errors"],
                "cost_usd": _f(r["cost"]),
            }
            for r in by_agent.order_by(cost_desc, "-calls")
        ],
        "by_origin": [
            {
                "origin": r["origin"],
                "label": origins.label(r["origin"]),
                "calls": r["calls"],
                "cost_usd": _f(r["cost"]),
            }
            for r in by_origin.order_by(cost_desc, "-calls")
        ],
        "by_error": [
            {
                "code": r["error_code"],
                "label": error_label(r["error_code"]),
                "calls": r["calls"],
            }
            for r in by_error.order_by("-calls")
        ],
    }


def report(days: int) -> dict[str, Any]:
    """Totals, breakdowns, daily series and budget of the last ``days`` days."""
    if days not in ALLOWED_DAYS:
        raise ValueError(f"days must be one of {ALLOWED_DAYS}")
    start, end = period(days)
    qs = events_between(start, end)
    return {
        "days": days,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "generated_at": timezone.now(),
        "totals": totals(qs),
        **_breakdowns(qs),
        "daily": daily_series(qs, start, end),
        "budget": budget.summary(AISettings.load()),
    }


def recent(limit: int = 15) -> list[AIEvent]:
    """Return the latest events (1 to 50), with the agent loaded."""
    return list(AIEvent.objects.select_related("agent")[: max(1, min(int(limit), 50))])
