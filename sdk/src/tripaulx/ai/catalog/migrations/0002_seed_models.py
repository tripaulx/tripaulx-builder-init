"""Seed the catalog with current OpenAI and Anthropic models and prices.

Prices are USD per 1 million tokens (input, cached input, output). Sources:
the OpenAI pricing table (2026-10-01) and the Anthropic model table
(2026-09-25). Rows are created with ``get_or_create`` on the unique pair, so
running again never duplicates rows nor overwrites admin edits; use
``manage.py ai_sync_catalog`` to update prices later. Reversing deletes
nothing: workspaces may be using these models.
"""

from datetime import date
from decimal import Decimal

from django.db import migrations

OPENAI_PRICES_ON = date(2026, 10, 1)
ANTHROPIC_PRICES_ON = date(2026, 9, 25)

#: provider, identifier, label, nickname, tier, highlighted, recommended,
#: order, description, (input, cached, output), extra fields.
MODELS = [
    (
        "openai",
        "gpt-6-luna",
        "GPT-6 Luna",
        "Fast",
        1,
        True,
        False,
        1,
        "Quick, high-volume tasks: summaries, classification and simple "
        "extraction. The cheapest of the line.",
        ("0.10", "0.01", "0.50"),
        {"accepts_minimal_effort": False},
    ),
    (
        "openai",
        "gpt-6.1-sol",
        "GPT-6.1 Sol",
        "Versatile",
        2,
        True,
        True,
        2,
        "Everyday work: analysis, reviews and well-grounded answers, close to "
        "Astra at a much lower cost.",
        ("2.00", "0.10", "10.00"),
        {"accepts_minimal_effort": False},
    ),
    (
        "openai",
        "gpt-6-astra",
        "GPT-6 Astra",
        "Expert",
        3,
        True,
        False,
        3,
        "The hardest work: long, multi-source analysis and conflicting "
        "evidence. The most capable and the most expensive.",
        ("10.00", "1.00", "50.00"),
        {"accepts_minimal_effort": False},
    ),
    (
        "openai",
        "gpt-5.6",
        "GPT-5.6",
        "",
        3,
        False,
        False,
        11,
        "Alias of GPT-5.6 Sol; follows the provider default if it changes.",
        ("4.00", "0.40", "20.00"),
        {},
    ),
    (
        "openai",
        "gpt-5.6-sol",
        "GPT-5.6 Sol",
        "",
        3,
        False,
        False,
        12,
        "The tier GPT-5.6 points to today.",
        ("4.00", "0.40", "20.00"),
        {},
    ),
    (
        "openai",
        "gpt-5.6-terra",
        "GPT-5.6 Terra",
        "",
        2,
        False,
        False,
        13,
        "Terra tier of GPT-5.6.",
        ("2.00", "0.20", "12.00"),
        {},
    ),
    (
        "openai",
        "gpt-5.6-luna",
        "GPT-5.6 Luna",
        "",
        1,
        False,
        False,
        14,
        "Luna tier of GPT-5.6.",
        ("0.20", "0.02", "1.20"),
        {},
    ),
    (
        "openai",
        "gpt-5",
        "GPT-5",
        "",
        2,
        False,
        False,
        20,
        "Previous generation, for prompts already tuned on it.",
        ("1.25", "0.125", "10.00"),
        {},
    ),
    (
        "openai",
        "gpt-5-mini",
        "GPT-5 mini",
        "",
        1,
        False,
        False,
        21,
        "Previous generation, balanced cost.",
        ("0.25", "0.025", "2.00"),
        {},
    ),
    (
        "openai",
        "gpt-5-nano",
        "GPT-5 nano",
        "",
        1,
        False,
        False,
        22,
        "Previous generation, the cheapest and fastest.",
        ("0.05", "0.005", "0.40"),
        {},
    ),
    (
        "anthropic",
        "claude-haiku-4-5-20251001",
        "Claude Haiku 4.5",
        "Fast",
        1,
        True,
        False,
        1,
        "Simple, speed-critical tasks: classification, extraction and short answers.",
        ("1.00", "0.10", "5.00"),
        {
            "uses_thinking_budget": True,
            "options": {"web_search_tool": "web_search_20250305"},
        },
    ),
    (
        "anthropic",
        "claude-sonnet-5-5",
        "Claude Sonnet 5.5",
        "Versatile",
        2,
        True,
        False,
        2,
        "Speed and capability for everyday work and high-volume workloads.",
        ("2.00", "0.20", "10.00"),
        {"accepts_minimal_effort": False, "options": {"fallbacks": "default"}},
    ),
    (
        "anthropic",
        "claude-opus-5-5",
        "Claude Opus 5.5",
        "Expert",
        3,
        True,
        True,
        3,
        "Anthropic's default model for complex reasoning and long, demanding work.",
        ("4.00", "0.20", "20.00"),
        {"accepts_minimal_effort": False, "options": {"fallbacks": "default"}},
    ),
]


def seed(apps, schema_editor):
    AIModel = apps.get_model("tpsdk_ai_catalog", "AIModel")
    for (
        provider,
        identifier,
        label,
        nickname,
        tier,
        highlighted,
        recommended,
        order,
        description,
        (entry, cached, output),
        extra,
    ) in MODELS:
        AIModel.objects.get_or_create(
            provider=provider,
            identifier=identifier,
            defaults={
                "label": label,
                "nickname": nickname,
                "cost_tier": tier,
                "highlighted": highlighted,
                "recommended": recommended,
                "order": order,
                "description": description,
                "active": True,
                "supports_reasoning": True,
                "input_price_usd_1m": Decimal(entry),
                "cached_price_usd_1m": Decimal(cached),
                "output_price_usd_1m": Decimal(output),
                "prices_updated_on": OPENAI_PRICES_ON
                if provider == "openai"
                else ANTHROPIC_PRICES_ON,
                **extra,
            },
        )


def unseed(apps, schema_editor):
    """Delete nothing: workspaces may be using these models."""


class Migration(migrations.Migration):
    dependencies = [("tpsdk_ai_catalog", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
