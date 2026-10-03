"""Event recording (success, error, prior failure, content off) and the cap."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.utils import timezone

from tripaulx.ai.models import AIEvent
from tripaulx.ai.providers import AIRequest, AIResponse
from tripaulx.ai.providers.errors import make
from tripaulx.ai.services import budget, events, execution
from tripaulx.core.testing import TenantTestCase

from .helpers import OPENAI_SEND, configure_ai, new_agent, openai_response


class RecordTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.settings, self.model = configure_ai()
        self.agent = new_agent("Reviewer")
        self.user = self.make_user(email="ana@example.com", first_name="Ana")
        self.ctx = events.EventContext(
            execution_id=uuid4(), origin="playground", user=self.user, agent=self.agent
        )
        self.request = AIRequest(
            model=self.model, instructions="sys", input="u", api_key="k"
        )

    def _record(self, response: AIResponse) -> AIEvent:
        return events.record(response, self.request, self.ctx, settings=self.settings)

    def test_success_with_cost_and_frozen_labels(self):
        ev = self._record(
            AIResponse(
                ok=True,
                text="out",
                input_tokens=1_000_000,
                output_tokens=0,
                latency_ms=321,
                http_status=200,
            )
        )
        assert ev.status == "success" and ev.cost_usd == Decimal("2")
        assert ev.input_price_usd_1m == Decimal("2.00")
        assert (ev.agent_label, ev.user_label) == ("Reviewer", "Ana")
        assert (ev.model_identifier, ev.provider) == ("gpt-5.6-terra", "openai")
        assert (ev.output_text, ev.system_prompt) == ("out", "sys")

    def test_provider_error_records_code_and_detail(self):
        error = make("rate_limited", http_status=429, detail="rate", provider="OpenAI")
        ev = self._record(AIResponse(ok=False, error=error, http_status=429))
        assert (ev.status, ev.error_code, ev.error_detail) == (
            "error",
            "rate_limited",
            "rate",
        )
        assert ev.cost_usd is None

    def test_labels_survive_deletion(self):
        ev = self._record(AIResponse(ok=True))
        self.user.delete()
        self.agent.delete(hard=True)
        ev.refresh_from_db()
        assert (
            ev.agent is None and ev.agent_label == "Reviewer" and ev.user_label == "Ana"
        )

    def test_content_off_keeps_only_metrics(self):
        self.settings.store_content = False
        ev = self._record(
            AIResponse(
                ok=True, text="secret", input_tokens=5, output_tokens=5, total_tokens=10
            )
        )
        assert (ev.system_prompt, ev.input_text, ev.output_text, ev.raw_response) == (
            "",
            "",
            "",
            None,
        )
        assert ev.total_tokens == 10

    def test_run_without_content_keeps_only_metrics(self):
        with mock.patch.object(*OPENAI_SEND, return_value=openai_response("opinion")):
            r = execution.run(
                self.agent, "private text", origin="api", store_content=False
            )
        assert r.ok and r.text == "opinion"
        ev = AIEvent.objects.get()
        assert not (
            ev.system_prompt or ev.input_text or ev.output_text or ev.raw_response
        )
        assert ev.total_tokens == 120 and ev.cost_usd is not None

    def test_prior_failure_has_no_http(self):
        ev = events.record_failure(
            make("no_key", provider="OpenAI"), self.ctx, model=self.model
        )
        assert (ev.status, ev.http_status, ev.error_code) == ("error", None, "no_key")

    def test_web_searches_are_billed_on_top(self):
        ev = self._record(
            AIResponse(ok=True, input_tokens=100, output_tokens=20, web_searches=3)
        )
        # 100 x $2/1M + 20 x $12/1M = 0.00044; + 3 searches x $0.01.
        assert ev.cost_usd == Decimal("0.03044") and ev.web_searches == 3


class BudgetTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.settings, _ = configure_ai()

    def _event(self, cost: str, *, days_ago: int = 0) -> None:
        ev = AIEvent.objects.create(
            execution_id=uuid4(),
            origin="playground",
            status="success",
            cost_usd=Decimal(cost),
        )
        if days_ago:
            AIEvent.objects.filter(pk=ev.pk).update(
                created_at=timezone.now() - timedelta(days=days_ago)
            )

    def test_sums_today_only(self):
        self._event("1.50")
        self._event("9.00", days_ago=1)
        assert budget.spent_today_usd() == Decimal("1.50")

    def test_no_cap_never_reached_and_cap_reached(self):
        self._event("1.00")
        assert budget.check(self.settings) is None
        self.settings.daily_cap_usd = Decimal("1.00")
        error = budget.check(self.settings)
        assert error.code == "daily_cap_reached" and "1.00" in error.message
        summary = budget.summary(self.settings)
        assert summary["reached"] and summary["remaining_usd"] == 0.0
