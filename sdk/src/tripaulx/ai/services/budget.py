"""Daily AI spending cap (per workspace).

The check runs ONCE, before the whole run, not at each step: a run that
starts below the cap finishes, so the overshoot is at most one run, and a
team consolidation is never cut in the middle.

"Today" is the LOCAL day (``TIME_ZONE``): the cap is a management rule of
the workspace, and its day turns at its midnight.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from tripaulx.ai.models import AIEvent
from tripaulx.ai.providers import AIError
from tripaulx.ai.providers.errors import make


def spent_today_usd() -> Decimal:
    """Sum of ``cost_usd`` of today's events (unpriced ones do not count)."""
    today = timezone.localdate()
    total = AIEvent.objects.filter(created_at__date=today).aggregate(
        total=Sum("cost_usd")
    )["total"]
    return total or Decimal(0)


def check(settings: Any) -> AIError | None:
    """``None`` when a run may start; the cap error once it is reached."""
    cap = getattr(settings, "daily_cap_usd", None)
    if cap is None:
        return None
    if spent_today_usd() >= cap:
        return make("daily_cap_reached", cap=f"{cap:.2f}")
    return None


def summary(settings: Any) -> dict[str, Any]:
    """Summarize today's budget for the UI."""
    cap = getattr(settings, "daily_cap_usd", None)
    spent = spent_today_usd()
    remaining = (cap - spent) if cap is not None else None
    return {
        "cap_usd": float(cap) if cap is not None else None,
        "spent_today_usd": float(spent),
        "remaining_usd": float(max(remaining, Decimal(0)))
        if remaining is not None
        else None,
        "reached": cap is not None and spent >= cap,
    }
