"""Key service: one active key per provider, wiped secrets, frozen actors."""

from __future__ import annotations

from django.db import IntegrityError, transaction
import pytest

from tripaulx.ai.models import AIKey, AISettings, KeyClosedReason
from tripaulx.ai.services import keys
from tripaulx.core.testing import TenantTestCase


class KeyServiceTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.ana = self.make_user(
            email="ana@example.com", first_name="Ana", last_name="Lima"
        )
        self.bia = self.make_user(email="bia@example.com")

    def test_add_stores_encrypted_and_records_who(self):
        key = keys.add("openai", "sk-first", by=self.ana)
        assert key.is_active and "sk-first" not in key.api_key_encrypted
        assert key.api_key == "sk-first"
        assert (key.created_by, key.created_by_label) == (self.ana, "Ana Lima")
        assert AISettings.load().api_key == "sk-first"
        assert (
            keys.add("anthropic", "x", by=self.bia).created_by_label
            == "bia@example.com"
        )

    def test_one_active_key_per_provider(self):
        openai_key = keys.add("openai", "sk-openai", by=self.ana)
        anthropic_key = keys.add("anthropic", "sk-ant", by=self.ana)
        assert keys.active("openai") == openai_key
        assert keys.active("anthropic") == anthropic_key
        settings = AISettings.load()
        assert settings.api_key == "sk-openai"
        settings.provider = "anthropic"
        assert settings.api_key == "sk-ant"

    def test_add_replaces_only_the_same_provider_and_wipes_the_secret(self):
        first = keys.add("openai", "sk-1", by=self.ana)
        other = keys.add("anthropic", "sk-ant", by=self.ana)
        second = keys.add("openai", "sk-2", by=self.bia)
        first.refresh_from_db()
        other.refresh_from_db()
        assert not first.is_active and first.closed_reason == KeyClosedReason.REPLACED
        assert (first.closed_by, first.closed_by_label) == (self.bia, "bia@example.com")
        assert first.api_key_encrypted == "" and first.api_key == ""
        assert other.is_active
        assert keys.active("openai") == second

    def test_database_refuses_two_active_keys_of_one_provider(self):
        AIKey.objects.create(provider="openai", api_key_encrypted="a")
        with self.assertRaises(IntegrityError), transaction.atomic():
            AIKey.objects.create(provider="openai", api_key_encrypted="b")

    def test_delete_is_soft_and_records_who(self):
        keys.add("openai", "sk-1", by=self.ana)
        closed = keys.delete("openai", by=self.bia)
        closed.refresh_from_db()
        assert AIKey.objects.count() == 1
        assert closed.closed_reason == KeyClosedReason.DELETED
        assert closed.closed_by_label == "bia@example.com"
        assert closed.api_key_encrypted == ""
        assert not AISettings.load().api_key_configured
        assert keys.delete("openai", by=self.bia) is None

    def test_labels_survive_user_removal(self):
        keys.add("openai", "sk-1", by=self.ana)
        keys.delete("openai", by=self.bia)
        self.ana.delete()
        self.bia.delete()
        row = AIKey.objects.get()
        assert row.created_by is None and row.closed_by is None
        assert (row.created_by_label, row.closed_by_label) == (
            "Ana Lima",
            "bia@example.com",
        )

    def test_refuses_empty_header_unsafe_and_unknown_provider(self):
        for provider, value in (("openai", "  "), ("openai", "sk-aМb"), ("nope", "k")):
            with pytest.raises(keys.InvalidKey):
                keys.add(provider, value, by=self.ana)
        assert not AIKey.objects.exists()

    def test_history_lists_closed_keys_of_the_provider(self):
        keys.add("openai", "sk-1", by=self.ana)
        keys.add("openai", "sk-2", by=self.ana)
        keys.delete("openai", by=self.bia)
        keys.add("anthropic", "a", by=self.ana)
        history = keys.history("openai")
        assert [k.closed_reason for k in history] == ["deleted", "replaced"]
        assert keys.history("anthropic") == []

    def test_unreadable_token_is_not_configured(self):
        AIKey.objects.create(provider="openai", api_key_encrypted="not-a-fernet-token")
        assert not AISettings.load().api_key_configured
