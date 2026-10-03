"""Retention purge as a ``django.tasks`` task (schedule it daily)."""

from __future__ import annotations

from django.tasks import task

from tripaulx.ai.services import retention


@task()
def purge_ai_content(days: int | None = None) -> dict[str, int]:
    """Purge old event content in every workspace; return counts per schema."""
    return retention.purge_all_workspaces(days=days)
