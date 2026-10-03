from django.conf import settings
from tripaulx.accounts.models import Role
from tripaulx.ai.catalog.models import AIModel
from tripaulx.ai.conf import app_settings
from tripaulx.core.testing import TenantAPITestCase


def test_ai_apps_are_installed_and_configured():
    assert "tripaulx.ai.catalog" in settings.SHARED_APPS
    assert "tripaulx.ai" in settings.TENANT_APPS
    assert app_settings.AI_BASE_PROMPT
    assert app_settings.AI_RUN_DEADLINE_S >= app_settings.AI_TIMEOUT_S


class AIRoutesTests(TenantAPITestCase):
    def test_catalog_is_seeded_and_served(self):
        assert AIModel.objects.filter(provider="anthropic").exists()
        response = self.api_client().get("/api/v1/ai/providers/")
        assert response.status_code == 200
        assert {p["value"] for p in response.data} >= {"openai", "anthropic"}

    def test_only_admins_change_the_settings(self):
        member = self.api_client()
        assert (
            member.patch("/api/v1/ai/settings/", {"enabled": True}).status_code == 403
        )
        admin = self.make_user(email="owner@example.com", role=Role.OWNER)
        response = self.api_client(admin).patch(
            "/api/v1/ai/settings/", {"enabled": True}, format="json"
        )
        assert response.status_code == 200 and response.data["enabled"] is True
