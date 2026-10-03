"""``/api/v1/ai/key/``: admins change keys, members read the state only."""

from __future__ import annotations

from tripaulx.ai.models import AIKey, AISettings

from .helpers import AITestCase

URL = "/api/v1/ai/key/"


class KeyApiTests(AITestCase):
    def _state(self, response, provider="openai"):
        return next(s for s in response.data if s["provider"] == provider)

    def test_requires_authentication(self):
        anon = self.anon_api_client()
        assert anon.get(URL).status_code == 401
        assert anon.post(URL, {"provider": "openai", "api_key": "x"}).status_code == 401

    def test_members_read_but_never_write(self):
        assert self.member_api.get(URL).status_code == 200
        body = {"provider": "openai", "api_key": "sk-x"}
        assert self.member_api.post(URL, body, format="json").status_code == 403
        assert self.member_api.delete(f"{URL}?provider=openai").status_code == 403
        assert not AIKey.objects.exists()

    def test_get_lists_every_provider(self):
        response = self.member_api.get(URL)
        assert {s["provider"] for s in response.data} >= {"openai", "anthropic"}
        state = self._state(response, "anthropic")
        assert state["label"] == "Anthropic"
        assert state["active"] is None and state["history"] == []

    def test_admin_adds_without_the_key_coming_back(self):
        body = {"provider": "anthropic", "api_key": "sk-ant-secret-value"}
        response = self.admin_api.post(URL, body, format="json")
        assert response.status_code == 201
        assert response.data["provider"] == "anthropic"
        assert response.data["active"]["created_by"] == "Ana"
        assert response.data["active"]["readable"]
        content = str(response.content)
        assert "sk-ant-secret-value" not in content and "api_key" not in content
        assert self._state(self.member_api.get(URL), "openai")["active"] is None

    def test_replace_and_delete_leave_history(self):
        self.admin_api.post(URL, {"provider": "openai", "api_key": "k1"}, format="json")
        response = self.admin_api.post(
            URL, {"provider": "openai", "api_key": "k2"}, format="json"
        )
        assert response.data["history"][0]["closed_reason"] == "replaced"
        assert AISettings.load().api_key == "k2"
        response = self.admin_api.delete(f"{URL}?provider=openai")
        assert response.status_code == 200 and response.data["active"] is None
        assert response.data["history"][0]["closed_reason_label"] == "Deleted"
        assert response.data["history"][0]["closed_by"] == "Ana"

    def test_invalid_keys_and_providers_are_400(self):
        bad = [
            {"provider": "openai", "api_key": ""},
            {"provider": "openai", "api_key": "sk-aМb"},
            {"provider": "nope", "api_key": "k"},
        ]
        for body in bad:
            response = self.admin_api.post(URL, body, format="json")
            assert response.status_code == 400
        assert "U+041C" in str(
            self.admin_api.post(URL, bad[1], format="json").data["api_key"][0]
        )
        assert self.admin_api.delete(f"{URL}?provider=nope").status_code == 400
        assert not AIKey.objects.exists()

    def test_nobody_reads_the_key_afterwards(self):
        self.admin_api.post(
            URL, {"provider": "openai", "api_key": "sk-never"}, format="json"
        )
        for response in (
            self.admin_api.get(URL),
            self.admin_api.get("/api/v1/ai/settings/"),
        ):
            assert "sk-never" not in str(response.content)
            assert "api_key_encrypted" not in str(response.content)
