"""Runtime: single runs, precedence, teams (brief, order, abort) and deadline."""

from __future__ import annotations

from decimal import Decimal
from unittest import mock

from django.test import override_settings
import openai

from tripaulx.ai.models import AgentRole, AgentSkill, AIEvent, TeamMember
from tripaulx.ai.services import execution
from tripaulx.core.testing import TenantTestCase

from .helpers import (
    ANTHROPIC_SEND,
    OPENAI_SEND,
    anthropic_response,
    configure_ai,
    new_agent,
    openai_response,
    published_skill,
    sdk_error,
)


class SingleRunTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.settings, self.model = configure_ai()
        self.agent = new_agent("Solo", input_template="CTX={context}\n{input}")

    def test_one_call_one_event_and_totals(self):
        raw = openai_response("opinion", input_tokens=1000, output_tokens=100)
        with mock.patch.object(*OPENAI_SEND, return_value=raw) as send:
            r = execution.run(self.agent, "document", origin="playground", context="c1")
        assert r.ok and r.text == "opinion"
        assert [s.step for s in r.steps] == ["single"]
        assert (r.input_tokens, r.output_tokens, r.total_tokens) == (1000, 100, 1100)
        assert r.cost_usd == Decimal("0.003200") and not r.cost_unknown
        event = AIEvent.objects.get()
        assert (event.step, event.position, event.status) == ("single", 0, "success")
        assert event.execution_id == r.execution_id and event.provider == "openai"
        _key, params, _timeout = send.call_args.args
        assert params["input"] == "CTX=c1\ndocument"
        assert "You are Solo." in params["instructions"]

    def test_precedence_skill_agent_settings(self):
        configure_ai(identifier="gpt-5-mini", key=None)
        self.settings.model_identifier = self.model.identifier
        self.settings.effort = "low"
        self.settings.save()
        self.agent.effort = "high"
        self.agent.save()
        skill = published_skill("Quick")
        skill.model_identifier = "gpt-5-mini"
        skill.save()
        AgentSkill.objects.create(agent=self.agent, skill=skill, order=0)
        with mock.patch.object(*OPENAI_SEND, return_value=openai_response()) as send:
            assert execution.run(self.agent, "doc", origin="playground").ok
        params = send.call_args.args[1]
        assert params["model"] == "gpt-5-mini"
        assert params["reasoning"] == {"effort": "high"}
        assert "--- SKILL: Quick (v1) ---" in params["instructions"]
        assert AIEvent.objects.get().skills[0]["slug"] == "quick"

    def test_provider_refusal_is_ok_false_and_an_error_event(self):
        with mock.patch.object(*OPENAI_SEND, side_effect=sdk_error(openai, 429)):
            r = execution.run(self.agent, "doc", origin="playground")
        assert not r.ok and r.error.code == "rate_limited"
        assert AIEvent.objects.get().status == "error"

    def test_no_price_marks_unknown_cost(self):
        configure_ai(prices=None, key=None)
        with mock.patch.object(*OPENAI_SEND, return_value=openai_response()):
            r = execution.run(self.agent, "doc", origin="playground")
        assert r.ok and r.cost_usd is None and r.cost_unknown

    def test_runs_on_anthropic_with_its_own_key(self):
        configure_ai(provider="anthropic", identifier="claude-sonnet-5-5", key="sk-ant")
        with mock.patch.object(
            *ANTHROPIC_SEND, return_value=anthropic_response("hi")
        ) as s:
            r = execution.run(self.agent, "doc", origin="playground")
        assert r.ok and r.text == "hi"
        assert s.call_args.args[0] == "sk-ant"
        assert AIEvent.objects.get().provider == "anthropic"


class TeamTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        configure_ai()
        self.coord = new_agent("Coordinator", role=AgentRole.COORDINATOR)
        self.a, self.b = new_agent("Finance"), new_agent("Legal")
        TeamMember.objects.create(coordinator=self.coord, specialist=self.b, order=1)
        TeamMember.objects.create(coordinator=self.coord, specialist=self.a, order=0)

    def test_runs_in_order_chains_the_brief_and_consolidates(self):
        answers = [
            openai_response("finance"),
            openai_response("legal"),
            openai_response("final"),
        ]
        with mock.patch.object(*OPENAI_SEND, side_effect=answers) as send:
            r = execution.run(self.coord, "doc", origin="playground")
        assert r.ok and r.text == "final"
        assert [s.agent.name for s in r.steps] == ["Finance", "Legal", "Coordinator"]
        assert [s.step for s in r.steps] == [
            "specialist",
            "specialist",
            "consolidation",
        ]
        inputs = [c.args[1]["input"] for c in send.call_args_list]
        assert "finance" not in inputs[0]
        assert "### Finance\nfinance" in inputs[1] and "legal" in inputs[2]
        assert {e.execution_id for e in AIEvent.objects.all()} == {r.execution_id}
        assert r.total_tokens == 3 * 120

    def test_stops_at_the_first_error(self):
        with mock.patch.object(
            *OPENAI_SEND, side_effect=[sdk_error(openai, 500), openai_response()]
        ) as send:
            r = execution.run(self.coord, "doc", origin="playground")
        assert r.error.code == "provider_unavailable"
        assert send.call_count == 1 and len(r.steps) == 1
        assert AIEvent.objects.count() == 1

    def test_inactive_member_skipped_and_empty_team_fails(self):
        self.a.active = False
        self.a.save()
        with mock.patch.object(
            *OPENAI_SEND, side_effect=[openai_response(), openai_response()]
        ) as send:
            assert execution.run(self.coord, "doc", origin="playground").ok
        assert send.call_count == 2
        self.b.delete()
        with mock.patch.object(*OPENAI_SEND) as send:
            r = execution.run(self.coord, "doc", origin="playground")
        assert r.error.code == "empty_team"
        send.assert_not_called()

    @override_settings(TRIPAULX={"AI_RUN_DEADLINE_S": 1})
    def test_exhausted_deadline_does_not_call(self):
        with mock.patch.object(*OPENAI_SEND) as send:
            r = execution.run(self.coord, "doc", origin="playground")
        assert r.error.code == "timeout"
        send.assert_not_called()
