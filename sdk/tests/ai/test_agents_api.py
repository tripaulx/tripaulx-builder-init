"""Agents API: admin-only writes, ordered team/skills, validations, run."""

from __future__ import annotations

from unittest import mock

import openai

from tripaulx.ai.models import Agent, AgentRole

from .helpers import (
    OPENAI_SEND,
    AITestCase,
    configure_ai,
    new_agent,
    openai_response,
    published_skill,
    sdk_error,
)

URL = "/api/v1/ai/agents/"
DOCS = "docs.example.com"


class AgentApiTests(AITestCase):
    def setUp(self):
        super().setUp()
        configure_ai()
        self.a, self.b = new_agent("Finance"), new_agent("Legal")
        self.skill = published_skill("Style")

    def _body(self, **extra):
        body = {
            "name": "Document reviewer",
            "role": "coordinator",
            "instructions": "Consolidate.",
            "input_template": "{context}\n{input}",
            "team": [str(self.b.pk), str(self.a.pk)],
            "skills": [{"id": str(self.skill.pk), "required": False}],
        }
        body.update(extra)
        return body

    def test_members_read_but_never_write(self):
        assert self.anon_api_client().get(URL).status_code == 401
        assert self.member_api.get(URL).status_code == 200
        assert self.member_api.post(URL, self._body(), format="json").status_code == 403
        detail = f"{URL}{self.a.pk}/"
        assert (
            self.member_api.patch(detail, {"name": "x"}, format="json").status_code
            == 403
        )
        assert self.member_api.delete(detail).status_code == 403
        assert self.member_api.post(f"{detail}duplicate/").status_code == 403

    def test_admin_creates_with_ordered_team_and_skills(self):
        r = self.admin_api.post(URL, self._body(), format="json")
        assert r.status_code == 201, r.data
        assert r.data["slug"] == "document-reviewer"
        assert r.data["team"] == [str(self.b.pk), str(self.a.pk)]
        assert [m["name"] for m in r.data["team_detail"]] == ["Legal", "Finance"]
        assert r.data["skills"] == [{"id": str(self.skill.pk), "required": False}]
        assert r.data["skills_detail"][0]["published_version"] == 1
        assert r.data["created_by"] == "Ana"
        team = [str(self.a.pk), str(self.b.pk)]
        r2 = self.admin_api.patch(
            f"{URL}{r.data['id']}/", {"team": team}, format="json"
        )
        assert r2.status_code == 200 and r2.data["team"] == team

    def test_validations(self):
        cases = [
            ({"team": []}, "team"),
            ({"role": "specialist"}, "team"),
            ({"team": [str(self.a.pk), str(self.a.pk)]}, "team"),
            ({"input_template": "{context}"}, "input_template"),
            ({"name": "finance"}, "name"),
            ({"output_schema": {"type": "array"}}, "output_schema"),
            ({"temperature": "3"}, "temperature"),
            ({"instructions": " "}, "instructions"),
            ({"model_identifier": "claude-opus-5-5"}, "model_identifier"),
            ({"web_search_domains": ["not a domain"]}, "web_search_domains"),
        ]
        for extra, field in cases:
            r = self.admin_api.post(URL, self._body(**extra), format="json")
            assert r.status_code == 400 and field in r.data, (extra, r.data)

    def test_team_members_must_be_active_specialists(self):
        coord = new_agent("Other", role=AgentRole.COORDINATOR)
        r = self.admin_api.post(URL, self._body(team=[str(coord.pk)]), format="json")
        assert "not a specialist" in r.data["team"][0]
        self.a.active = False
        self.a.save()
        r = self.admin_api.post(URL, self._body(team=[str(self.a.pk)]), format="json")
        assert "inactive" in r.data["team"][0]

    def test_role_change_blocked_while_in_a_team(self):
        assert self.admin_api.post(URL, self._body(), format="json").status_code == 201
        r = self.admin_api.patch(
            f"{URL}{self.a.pk}/", {"role": "coordinator"}, format="json"
        )
        assert r.status_code == 400 and "in the team of" in r.data["role"][0]

    def test_domains_are_cleaned(self):
        domains = ["https://Docs.Example.com/?q=x", DOCS, " "]
        r = self.admin_api.patch(
            f"{URL}{self.a.pk}/",
            {"web_search": True, "web_search_domains": domains},
            format="json",
        )
        assert r.status_code == 200 and r.data["web_search_domains"] == [DOCS]

    def test_soft_delete_filters_and_duplicate(self):
        r = self.admin_api.post(URL, self._body(), format="json")
        copy = self.admin_api.post(f"{URL}{r.data['id']}/duplicate/")
        assert (
            copy.status_code == 201 and copy.data["name"] == "Document reviewer (copy)"
        )
        assert not copy.data["active"] and copy.data["team"] == r.data["team"]
        assert self.admin_api.delete(f"{URL}{self.a.pk}/").status_code == 204
        assert Agent.all_objects.filter(pk=self.a.pk).exists()
        assert self.member_api.get(f"{URL}{self.a.pk}/").status_code == 404
        names = [x["name"] for x in self.member_api.get(URL, {"active": "true"}).data]
        assert "Legal" in names and "Document reviewer (copy)" not in names


class RunApiTests(AITestCase):
    def setUp(self):
        super().setUp()
        configure_ai()
        self.agent = new_agent("Finance")
        self.url = f"{URL}{self.agent.pk}/run/"

    def test_any_member_runs(self):
        raw = openai_response("opinion", input_tokens=1000, output_tokens=100)
        with mock.patch.object(*OPENAI_SEND, return_value=raw):
            r = self.member_api.post(self.url, {"input": "doc"}, format="json")
        assert r.status_code == 200, r.data
        assert r.data["ok"] and r.data["text"] == "opinion"
        assert r.data["tokens"] == {"input": 1000, "output": 100, "total": 1100}
        assert isinstance(r.json()["cost_usd"], float)
        assert r.data["steps"][0]["step"] == "single" and r.data["error"] is None
        assert "sk-test" not in str(r.content)

    def test_provider_refusal_is_200_ok_false(self):
        with mock.patch.object(*OPENAI_SEND, side_effect=sdk_error(openai, 401)):
            r = self.member_api.post(self.url, {"input": "doc"}, format="json")
        assert r.status_code == 200 and not r.data["ok"]
        assert r.data["error"]["code"] == "key_rejected"
        assert r.data["error"]["http_status"] == 401

    def test_empty_body_400_get_405_and_size_limit(self):
        assert (
            self.member_api.post(self.url, {"input": ""}, format="json").status_code
            == 400
        )
        assert self.member_api.get(self.url).status_code == 405
        with self.settings(TRIPAULX={"AI_MAX_INPUT_CHARS": 5}):
            r = self.member_api.post(self.url, {"input": "too long"}, format="json")
        assert r.status_code == 400 and "input" in r.data
