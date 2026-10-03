"""Skills API: admin-only writes, publish, versions and duplicate."""

from __future__ import annotations

from tripaulx.ai.models import AgentSkill, Skill

from .helpers import AITestCase, configure_ai, new_agent

URL = "/api/v1/ai/skills/"


class SkillApiTests(AITestCase):
    def setUp(self):
        super().setUp()
        configure_ai()

    def _create(self, **body):
        body = {"name": "Style", "instructions": "Be formal.", **body}
        return self.admin_api.post(URL, body, format="json")

    def test_crud_and_permissions(self):
        r = self._create()
        assert r.status_code == 201, r.data
        assert not r.data["is_published"] and r.data["has_pending_draft"]
        assert r.data["slug"] == "style"
        body = {"name": "X", "instructions": "y"}
        assert self.member_api.post(URL, body, format="json").status_code == 403
        assert self.member_api.get(URL).status_code == 200
        detail = f"{URL}{r.data['id']}/"
        assert self.member_api.post(f"{detail}publish/").status_code == 403
        r2 = self.admin_api.patch(detail, {"description": "d"}, format="json")
        assert r2.data["description"] == "d"
        assert self.admin_api.delete(detail).status_code == 204
        assert Skill.all_objects.filter(pk=r.data["id"]).exists()

    def test_validations(self):
        assert "instructions" in self._create(instructions=" ").data
        assert self._create().status_code == 201
        assert "name" in self._create(name="style").data
        assert (
            "model_identifier" in self._create(name="B", model_identifier="nope").data
        )

    def test_publish_and_versions(self):
        sid = self._create(instructions="v1").data["id"]
        published = self.admin_api.post(
            f"{URL}{sid}/publish/", {"note": "first"}, format="json"
        )
        assert published.status_code == 200, published.data
        assert published.data["published_version"] == 1
        assert not published.data["has_pending_draft"]
        again = self.admin_api.post(f"{URL}{sid}/publish/", {}, format="json")
        assert again.status_code == 400
        self.admin_api.patch(f"{URL}{sid}/", {"instructions": "v2"}, format="json")
        assert self.member_api.get(f"{URL}{sid}/").data["has_pending_draft"]
        second = self.admin_api.post(f"{URL}{sid}/publish/", {}, format="json")
        assert second.data["published_version"] == 2
        versions = self.member_api.get(f"{URL}{sid}/versions/").data
        assert [v["number"] for v in versions] == [2, 1]
        assert versions[0]["published_by"] == "Ana" and versions[1]["note"] == "first"

    def test_agents_of_the_skill_and_duplicate(self):
        r = self._create()
        agent = new_agent("Reviewer")
        AgentSkill.objects.create(agent=agent, skill_id=r.data["id"], order=0)
        assert self.member_api.get(f"{URL}{r.data['id']}/").data["agents"][0][
            "name"
        ] == ("Reviewer")
        copy = self.admin_api.post(f"{URL}{r.data['id']}/duplicate/")
        assert copy.status_code == 201 and copy.data["name"] == "Style (copy)"
        assert not copy.data["is_published"]
