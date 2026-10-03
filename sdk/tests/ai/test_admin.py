"""Admin of the AI settings: the key goes through the service, never shown."""

from __future__ import annotations

from django.contrib.admin.sites import site

from tripaulx.ai.models import AIKey, AISettings
from tripaulx.ai.services import keys

from .helpers import AITestCase, configure_ai


def _form(**data):
    from tripaulx.ai.admin import AISettingsForm

    base = {
        "enabled": True,
        "provider": "openai",
        "model_identifier": "gpt-5.6-terra",
        "retention_days": 90,
        "store_content": True,
    }
    base.update(data)
    return AISettingsForm(data=base, instance=AISettings.load())


class SettingsAdminFormTests(AITestCase):
    def test_refuses_header_unsafe_key_and_accepts_a_normal_one(self):
        form = _form(new_api_key="sk-proj-aaaМbbb")
        assert not form.is_valid() and "U+041C" in str(form.errors["new_api_key"])
        assert _form(new_api_key="sk-proj-" + "a" * 150).is_valid()

    def test_model_must_belong_to_the_provider(self):
        form = _form(provider="anthropic")
        assert not form.is_valid() and "model_identifier" in form.errors
        assert _form(
            provider="anthropic", model_identifier="claude-haiku-4-5-20251001"
        ).is_valid()

    def test_one_key_action_at_a_time(self):
        assert not _form(new_api_key="sk-a", delete_api_key=True).is_valid()

    def test_save_adds_the_key_with_the_actor(self):
        form = _form(new_api_key="sk-from-admin")
        assert form.is_valid(), form.errors
        request = type("Request", (), {"user": self.admin})()
        site._registry[AISettings].save_model(
            request, form.save(commit=False), form, True
        )
        key = keys.active("openai")
        assert key.api_key == "sk-from-admin" and key.created_by == self.admin

    def test_key_status_never_shows_the_value(self):
        configure_ai(key="sk-hidden")
        status = site._registry[AISettings].api_key_status(AISettings.load())
        assert "sk-hidden" not in status and "Ana" not in status
        assert "set on" in status

    def test_key_history_is_read_only(self):
        model_admin = site._registry[AIKey]
        request = type("Request", (), {"user": self.admin})()
        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert "api_key_encrypted" not in model_admin.get_readonly_fields(request)
