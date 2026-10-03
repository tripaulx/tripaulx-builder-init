"""Retention: purge event content older than the workspace's retention days.

The content of an event (system prompt, input, output, raw response and the
error detail, which may quote output) is cleared; the metrics (tokens, cost,
latency, status) stay, so the report keeps working. ``retention_days = 0``
keeps content forever.

:func:`purge_all_workspaces` walks every workspace schema; it is what the
``ai_purge_content`` command and the ``purge_ai_content`` task run.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone
from django_tenants.utils import (
    get_public_schema_name,
    get_tenant_model,
    schema_context,
)

from tripaulx.ai.models import AIEvent, AISettings

CONTENT_FIELDS = {
    "system_prompt": "",
    "input_text": "",
    "output_text": "",
    "raw_response": None,
    "error_detail": "",
}


def purge_content(*, days: int | None = None, now: datetime | None = None) -> int:
    """Clear the content of old events in the CURRENT schema; return the count.

    ``days`` overrides the settings (``None`` reads ``retention_days``).
    """
    if days is None:
        days = AISettings.load().retention_days
    if not days:
        return 0
    now = now or timezone.now()
    old = AIEvent.objects.filter(
        created_at__lt=now - timedelta(days=days), content_purged_at__isnull=True
    )
    return old.update(content_purged_at=now, **CONTENT_FIELDS)


def workspace_schemas() -> list[str]:
    """Return the schema of every workspace (the public schema excluded)."""
    with schema_context(get_public_schema_name()):
        return list(
            get_tenant_model()
            .objects.exclude(schema_name=get_public_schema_name())
            .values_list("schema_name", flat=True)
        )


def purge_all_workspaces(
    *, days: int | None = None, schemas: list[str] | None = None
) -> dict[str, int]:
    """Run :func:`purge_content` in each workspace; return counts per schema."""
    counts: dict[str, int] = {}
    for schema in schemas if schemas is not None else workspace_schemas():
        with schema_context(schema):
            counts[schema] = purge_content(days=days)
    return counts
