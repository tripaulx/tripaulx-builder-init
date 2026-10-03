"""Report and dashboard: shapes, zero-filled series, no-price and runs."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone
import pytest

from tripaulx.ai.models import AIEvent
from tripaulx.ai.services import dashboard, report
from tripaulx.core.testing import TenantTestCase

from .helpers import configure_ai, new_agent


class ReportTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        configure_ai()
        self.agent = new_agent("Reviewer")
        run1, run2 = uuid4(), uuid4()
        self._event(run1, "success", "0.10")
        self._event(run1, "success", "0.20")
        self._event(run2, "error", None, code="rate_limited")
        self._event(uuid4(), "success", None, model="unpriced")
        self._event(uuid4(), "success", "9.00", days_ago=40)

    def _event(self, run, status, cost, *, model="gpt-5.6-terra", code="", days_ago=0):
        ev = AIEvent.objects.create(
            execution_id=run,
            origin="playground",
            status=status,
            agent=self.agent,
            agent_label="Reviewer",
            provider="openai",
            model_identifier=model,
            error_code=code,
            cost_usd=Decimal(cost) if cost else None,
            total_tokens=10,
            latency_ms=100,
        )
        if days_ago:
            AIEvent.objects.filter(pk=ev.pk).update(
                created_at=timezone.now() - timedelta(days=days_ago)
            )

    def test_totals(self):
        t = report.report(30)["totals"]
        assert (t["calls"], t["success"], t["errors"], t["runs"]) == (4, 3, 1, 3)
        assert t["success_rate"] == 75.0
        assert t["cost_usd"] == pytest.approx(0.30)
        assert t["no_price"] == 1

    def test_breakdowns(self):
        r = report.report(30)
        models = {m["model"]: m for m in r["by_model"]}
        assert models["gpt-5.6-terra"]["cost_usd"] == pytest.approx(0.30)
        assert models["unpriced"]["no_price"] == 1
        assert r["by_agent"][0]["agent"] == "Reviewer"
        assert r["by_agent"][0]["runs"] == 3
        assert r["by_origin"][0]["label"] == "Playground"
        assert r["by_error"] == [
            {"code": "rate_limited", "label": "Usage limit or credits", "calls": 1}
        ]
        assert "cap_usd" in r["budget"]

    def test_daily_series_has_one_row_per_day(self):
        series = report.report(7)["daily"]
        assert len(series) == 7
        assert series[-1]["day"] == timezone.localdate().isoformat()
        assert series[-1]["calls"] == 4 and series[0]["calls"] == 0

    def test_invalid_days(self):
        with pytest.raises(ValueError):
            report.report(15)

    def test_dashboard(self):
        d = dashboard.dashboard()
        assert d["settings"]["ready"] and d["settings"]["provider_label"] == "OpenAI"
        assert d["agents"]["total"] == 1
        assert d["last_30_days"]["calls"] == 4 and d["last_30_days"]["no_price"] == 1
        assert d["today"]["calls"] == 4
        assert len(d["recent"]) == 5 and d["last_event"] is not None
