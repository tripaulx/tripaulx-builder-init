"""Events API: paginated metadata for members, content for admins only."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from tripaulx.ai.models import AIEvent

from .helpers import AITestCase, configure_ai, new_agent

URL = "/api/v1/ai/events/"


class EventApiTests(AITestCase):
    def setUp(self):
        super().setUp()
        configure_ai()
        self.agent = new_agent("Reviewer")
        self.run_id = uuid4()
        for i in range(25):
            AIEvent.objects.create(
                execution_id=self.run_id if i < 3 else uuid4(),
                origin="playground",
                status="error" if i == 0 else "success",
                error_code="no_key" if i == 0 else "",
                agent=self.agent,
                agent_label="Reviewer",
                provider="openai",
                model_identifier="gpt-5.6-terra",
                cost_usd=Decimal("0.01"),
                output_text="secret output",
                system_prompt="sys",
                error_detail="detail",
                skills=[{"id": "abc", "slug": "s", "name": "S", "version": 1}],
            )
        self.event = AIEvent.objects.first()

    def test_list_is_paginated_metadata(self):
        r = self.member_api.get(URL)
        assert r.status_code == 200 and r.data["count"] == 25
        assert len(r.data["results"]) == 20
        item = r.data["results"][0]
        assert "output_text" not in item and "system_prompt" not in item
        assert item["agent"]["name"] == "Reviewer"
        assert isinstance(r.json()["results"][0]["cost_usd"], float)
        assert len(self.member_api.get(URL, {"page": 2}).data["results"]) == 5

    def test_filters(self):
        api = self.member_api
        assert api.get(URL, {"status": "error"}).data["count"] == 1
        assert api.get(URL, {"execution_id": str(self.run_id)}).data["count"] == 3
        assert api.get(URL, {"error_code": "no_key"}).data["count"] == 1
        assert api.get(URL, {"skill": "abc"}).data["count"] == 25
        assert api.get(URL, {"provider": "anthropic"}).data["count"] == 0
        assert api.get(URL, {"origin": "test"}).data["count"] == 0
        r = api.get(URL, {"origin": "nope"})
        assert r.status_code == 400 and "origin" in r.data
        assert api.get(URL, {"days": "0"}).status_code == 400

    def test_content_is_for_admins_only(self):
        member = self.member_api.get(f"{URL}{self.event.pk}/")
        assert member.status_code == 200
        assert "secret output" not in str(member.content)
        assert "output_text" not in member.data and "error_detail" not in member.data
        admin = self.admin_api.get(f"{URL}{self.event.pk}/")
        assert admin.data["output_text"] == "secret output"
        assert admin.data["system_prompt"] == "sys"

    def test_report_recent_and_dashboard(self):
        r = self.member_api.get(f"{URL}report/", {"days": 7})
        assert r.status_code == 200 and r.data["totals"]["calls"] == 25
        assert len(r.data["daily"]) == 7
        assert self.member_api.get(f"{URL}report/", {"days": 15}).status_code == 400
        recent = self.member_api.get(f"{URL}recent/", {"limit": 3}).data
        assert len(recent) == 3 and "output_text" not in recent[0]
        d = self.member_api.get("/api/v1/ai/dashboard/")
        assert d.status_code == 200 and d.data["agents"]["total"] == 1
        assert d.data["last_event"]["agent_label"] == "Reviewer"
        assert len(d.data["recent"]) == 5 and "secret output" not in str(d.content)

    def test_read_only(self):
        assert self.admin_api.post(URL, {}, format="json").status_code == 405
        detail = f"{URL}{self.event.pk}/"
        assert self.admin_api.delete(detail).status_code == 405
        assert self.anon_api_client().get(URL).status_code == 401
