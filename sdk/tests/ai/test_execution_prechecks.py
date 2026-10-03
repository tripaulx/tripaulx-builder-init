"""Runtime pre-checks: nothing is sent, but every failure becomes an event."""

from __future__ import annotations

from decimal import Decimal
from unittest import mock
import uuid

from tripaulx.ai.models import AgentSkill, AIEvent, Skill
from tripaulx.ai.services import execution, keys
from tripaulx.core.testing import TenantTestCase

from .helpers import OPENAI_SEND, configure_ai, new_agent, openai_response


class PrecheckTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.settings, self.model = configure_ai()
        self.agent = new_agent("Solo")

    def _run(self, text="document"):
        with mock.patch.object(*OPENAI_SEND) as send:
            result = execution.run(self.agent, text, origin="playground")
        return result, send

    def test_empty_input(self):
        r, send = self._run("   ")
        assert r.error.code == "empty_input"
        send.assert_not_called()
        assert AIEvent.objects.get().error_code == "empty_input"

    def test_ai_disabled(self):
        self.settings.enabled = False
        self.settings.save()
        r, send = self._run()
        assert r.error.code == "ai_disabled"
        send.assert_not_called()

    def test_no_key_names_the_provider(self):
        keys.delete("openai", by=None)
        r, _ = self._run()
        assert r.error.code == "no_key" and "OpenAI" in r.error.message

    def test_key_of_another_provider_does_not_count(self):
        keys.delete("openai", by=None)
        keys.add("anthropic", "sk-ant-key", by=None)
        assert self._run()[0].error.code == "no_key"

    def test_no_model(self):
        self.settings.model_identifier = ""
        self.settings.save()
        r, send = self._run()
        assert r.error.code == "no_model"
        send.assert_not_called()

    def test_inactive_agent(self):
        self.agent.active = False
        self.agent.save()
        r, _ = self._run()
        assert r.error.code == "agent_inactive" and "Solo" in r.error.message

    def test_daily_cap(self):
        self.settings.daily_cap_usd = Decimal("0.01")
        self.settings.save()
        AIEvent.objects.create(
            execution_id=uuid.uuid4(),
            origin="playground",
            status="success",
            cost_usd=Decimal("5"),
        )
        r, send = self._run()
        assert r.error.code == "daily_cap_reached"
        send.assert_not_called()

    def test_unknown_provider(self):
        self.settings.provider = "nope"
        self.settings.save()
        assert self._run()[0].error.code == "provider_missing"

    def test_required_skill_without_version_fails_optional_is_skipped(self):
        skill = Skill.objects.create(name="Unpublished", instructions="x")
        link = AgentSkill.objects.create(agent=self.agent, skill=skill, required=True)
        r, send = self._run()
        assert r.error.code == "skill_not_published"
        send.assert_not_called()
        link.required = False
        link.save()
        with mock.patch.object(*OPENAI_SEND, return_value=openai_response()):
            assert execution.run(self.agent, "document", origin="playground").ok
