"""Shared catalog: public schema, seed, ``ai_sync_catalog`` and admin rights."""

from __future__ import annotations

from decimal import Decimal
from io import StringIO
import json
import os
import tempfile

from django.contrib.admin.sites import site
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import RequestFactory
from django_tenants.utils import get_public_schema_name, schema_context
import pytest

from tripaulx.ai.catalog.models import AIModel
from tripaulx.core.testing import TenantTestCase

SEEDED = {
    ("openai", "gpt-6-luna"),
    ("openai", "gpt-6.1-sol"),
    ("openai", "gpt-6-astra"),
    ("openai", "gpt-5.6"),
    ("openai", "gpt-5-mini"),
    ("anthropic", "claude-opus-5-5"),
    ("anthropic", "claude-sonnet-5-5"),
    ("anthropic", "claude-haiku-4-5-20251001"),
}


class CatalogTests(TenantTestCase):
    def test_table_lives_in_the_public_schema_only(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_schema FROM information_schema.tables "
                "WHERE table_name = %s",
                [AIModel._meta.db_table],
            )
            schemas = {row[0] for row in cursor.fetchall()}
        assert get_public_schema_name() in schemas
        assert connection.schema_name not in schemas
        assert AIModel.objects.exists()  # reachable from the workspace

    def test_seed_has_current_models_tiers_and_prices(self):
        rows = {(m.provider, m.identifier): m for m in AIModel.objects.all()}
        assert SEEDED <= set(rows)
        opus = rows[("anthropic", "claude-opus-5-5")]
        assert opus.output_price_usd_1m == Decimal("20.0000") and opus.recommended
        assert opus.options == {"fallbacks": "default"}
        haiku = rows[("anthropic", "claude-haiku-4-5-20251001")]
        assert haiku.uses_thinking_budget and haiku.cost_tier == 1
        luna = rows[("openai", "gpt-6-luna")]
        assert luna.highlighted and not luna.accepts_minimal_effort
        recommended = {k for k, m in rows.items() if m.recommended}
        assert recommended == {
            ("openai", "gpt-6.1-sol"),
            ("anthropic", "claude-opus-5-5"),
        }
        assert all(m.has_price for m in rows.values())

    def test_sync_creates_updates_and_keeps_admin_edits(self):
        AIModel.objects.filter(identifier="gpt-5").update(description="Edited")
        out = StringIO()
        call_command(
            "ai_sync_catalog",
            self._file(
                "json",
                [
                    {
                        "provider": "openai",
                        "identifier": "gpt-5",
                        "output_price_usd_1m": "9.5",
                    },
                    {"provider": "acme", "identifier": "acme-1", "label": "Acme One"},
                ],
            ),
            stdout=out,
        )
        gpt5 = AIModel.objects.get(identifier="gpt-5")
        assert (
            gpt5.output_price_usd_1m == Decimal("9.5") and gpt5.description == "Edited"
        )
        assert AIModel.objects.get(provider="acme").label == "Acme One"
        assert "1 created, 1 updated" in out.getvalue()

    def test_sync_toml_prices_only_and_errors(self):
        toml = (
            '[[models]]\nprovider = "openai"\nidentifier = "gpt-5"\n'
            'input_price_usd_1m = "1.5"\n\n'
            '[[models]]\nprovider = "x"\nidentifier = "new"\n'
        )
        call_command(
            "ai_sync_catalog",
            self._write("toml", toml),
            "--prices-only",
            stdout=StringIO(),
        )
        assert AIModel.objects.get(identifier="gpt-5").input_price_usd_1m == Decimal(
            "1.5"
        )
        assert not AIModel.objects.filter(identifier="new").exists()
        for bad in (
            [{"provider": "openai"}],
            [{"provider": "a", "identifier": "b", "nope": 1}],
            {"models": 3},
        ):
            with pytest.raises(CommandError):
                call_command(
                    "ai_sync_catalog", self._file("json", bad), stdout=StringIO()
                )

    def test_admin_edits_only_from_the_public_schema(self):
        model_admin = site._registry[AIModel]
        request = RequestFactory().get("/")
        request.user = self.make_user(
            email="root@example.com", is_staff=True, is_superuser=True
        )
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_add_permission(request)
        with schema_context(get_public_schema_name()):
            assert model_admin.has_change_permission(request)

    def _file(self, suffix, data):
        return self._write(suffix, json.dumps(data))

    def _write(self, suffix, text):
        handle = tempfile.NamedTemporaryFile("w", suffix=f".{suffix}", delete=False)
        handle.write(text)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name
