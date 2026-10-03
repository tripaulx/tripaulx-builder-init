"""``settings/`` and ``providers/``: admin-only writes, catalog grouped by provider."""

from __future__ import annotations

from django.test import override_settings

from tripaulx.ai.catalog.models import AIModel
from tripaulx.ai.models import AIKey, AISettings
from tripaulx.ai.services import keys

from .helpers import AITestCase

SETTINGS = "/api/v1/ai/settings/"
PROVIDERS = "/api/v1/ai/providers/"


class SettingsApiTests(AITestCase):
    def test_requires_authentication(self):
        assert self.anon_api_client().get(SETTINGS).status_code == 401

    def test_defaults(self):
        data = self.member_api.get(SETTINGS).data
        assert not data["enabled"] and data["provider"] == "openai"
        assert data["model_identifier"] == "" and not data["ready"]
        assert not data["api_key_configured"]

    def test_members_cannot_change_settings(self):
        response = self.member_api.patch(SETTINGS, {"enabled": True}, format="json")
        assert response.status_code == 403
        assert not AISettings.load().enabled

    def test_admin_saves_provider_model_and_enabled(self):
        body = {
            "enabled": True,
            "provider": "anthropic",
            "model_identifier": "claude-opus-5-5",
        }
        response = self.admin_api.patch(SETTINGS, body, format="json")
        assert response.status_code == 200, response.data
        assert response.data["provider_label"] == "Anthropic"
        assert response.data["model_label"] == "Claude Opus 5.5"
        response = self.admin_api.patch(SETTINGS, {"enabled": False}, format="json")
        assert response.data["model_identifier"] == "claude-opus-5-5"

    def test_model_must_match_the_provider_and_be_active(self):
        response = self.admin_api.patch(
            SETTINGS, {"model_identifier": "claude-opus-5-5"}, format="json"
        )
        assert response.status_code == 400 and "model_identifier" in response.data
        self.admin_api.patch(SETTINGS, {"model_identifier": "gpt-5"}, format="json")
        response = self.admin_api.patch(
            SETTINGS, {"provider": "anthropic"}, format="json"
        )
        assert response.status_code == 400 and "model_identifier" in response.data
        AIModel.objects.filter(identifier="gpt-5-mini").update(active=False)
        response = self.admin_api.patch(
            SETTINGS, {"model_identifier": "gpt-5-mini"}, format="json"
        )
        assert response.status_code == 400
        assert (
            self.admin_api.patch(
                SETTINGS, {"provider": "nope"}, format="json"
            ).status_code
            == 400
        )

    def test_the_key_never_enters_through_settings(self):
        body = {"api_key": "sk-injected", "api_key_encrypted": "x"}
        assert self.admin_api.patch(SETTINGS, body, format="json").status_code == 200
        assert not AIKey.objects.exists()

    def test_key_is_configured_but_never_shown(self):
        keys.add("openai", "sk-secret", by=None)
        response = self.member_api.get(SETTINGS)
        assert response.data["api_key_configured"]
        assert "sk-secret" not in str(response.content)


class ProvidersApiTests(AITestCase):
    def test_catalog_grouped_by_provider_with_cards_and_prices(self):
        data = self.member_api.get(PROVIDERS).data
        by_value = {p["value"]: p for p in data}
        assert by_value["openai"]["label"] == "OpenAI"
        sol = next(
            m for m in by_value["openai"]["models"] if m["identifier"] == "gpt-6.1-sol"
        )
        assert sol["highlighted"] and sol["recommended"] and sol["cost_tier"] == 2
        assert sol["prices"] == {"input": 2.0, "cached": 0.1, "output": 10.0}
        claude = {m["identifier"] for m in by_value["anthropic"]["models"]}
        assert {
            "claude-opus-5-5",
            "claude-sonnet-5-5",
            "claude-haiku-4-5-20251001",
        } <= claude

    def test_inactive_models_are_hidden_and_empty_providers_listed(self):
        AIModel.objects.filter(provider="anthropic").update(active=False)
        data = {p["value"]: p for p in self.member_api.get(PROVIDERS).data}
        assert data["anthropic"]["models"] == []

    @override_settings(
        TRIPAULX={"AI_PRICE_OVERRIDES": {"openai:gpt-5": {"input": "1", "output": "2"}}}
    )
    def test_price_override_is_what_the_picker_shows(self):
        data = {p["value"]: p for p in self.member_api.get(PROVIDERS).data}
        gpt5 = next(m for m in data["openai"]["models"] if m["identifier"] == "gpt-5")
        assert gpt5["prices"] == {"input": 1.0, "cached": None, "output": 2.0}
