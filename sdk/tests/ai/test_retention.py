"""Retention purge: old content cleared, metrics kept, per-workspace days."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from io import StringIO
from uuid import uuid4

from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from tripaulx.ai.models import AIEvent, AISettings
from tripaulx.ai.services import retention
from tripaulx.ai.tasks import purge_ai_content
from tripaulx.core.testing import TenantTestCase


class RetentionTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.old = self._event(days_ago=100)
        self.recent = self._event(days_ago=10)

    def _event(self, *, days_ago: int) -> AIEvent:
        ev = AIEvent.objects.create(
            execution_id=uuid4(),
            origin="playground",
            status="success",
            system_prompt="sys",
            input_text="in",
            output_text="out",
            raw_response={"id": "x"},
            error_detail="d",
            total_tokens=42,
            cost_usd=Decimal("0.5"),
        )
        AIEvent.objects.filter(pk=ev.pk).update(
            created_at=timezone.now() - timedelta(days=days_ago)
        )
        return ev

    def test_purges_old_content_and_keeps_metrics(self):
        assert retention.purge_content() == 1
        self.old.refresh_from_db()
        assert (self.old.system_prompt, self.old.input_text, self.old.output_text) == (
            "",
            "",
            "",
        )
        assert self.old.raw_response is None and self.old.error_detail == ""
        assert self.old.total_tokens == 42 and self.old.cost_usd == Decimal("0.5")
        assert self.old.content_purged_at is not None
        self.recent.refresh_from_db()
        assert (
            self.recent.output_text == "out" and self.recent.content_purged_at is None
        )
        assert retention.purge_content() == 0

    def test_uses_the_workspace_days_and_zero_keeps_forever(self):
        settings = AISettings.load()
        settings.retention_days = 0
        settings.save()
        assert retention.purge_content() == 0
        settings.retention_days = 7
        settings.save()
        assert retention.purge_content() == 2

    def test_command_walks_workspaces(self):
        out = StringIO()
        call_command("ai_purge_content", "--schema", connection.schema_name, stdout=out)
        assert f"{connection.schema_name}: 1" in out.getvalue()
        call_command("ai_purge_content", "--days", "5", stdout=out)
        assert AIEvent.objects.filter(content_purged_at__isnull=True).count() == 0

    def test_task_runs_in_every_workspace(self):
        counts = purge_ai_content.call()
        assert counts[connection.schema_name] == 1
        assert connection.schema_name in retention.workspace_schemas()
