"""Token cost (with overrides) and prompt assembly."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from django.test import override_settings

from tripaulx.ai.catalog.models import AIModel
from tripaulx.ai.conf import DEFAULT_BASE_PROMPT
from tripaulx.ai.services import prices, prompt


def _model(entry=None, out=None, cached=None) -> AIModel:
    return AIModel(
        provider="openai",
        identifier="m",
        input_price_usd_1m=Decimal(entry) if entry else None,
        output_price_usd_1m=Decimal(out) if out else None,
        cached_price_usd_1m=Decimal(cached) if cached else None,
    )


def test_cost_input_output_cache_and_rounding():
    assert prices.cost_usd(_model("2.00", "12.00"), 1_000_000, 500_000) == Decimal("8")
    assert prices.cost_usd(_model(None, "12.00"), 1000, 1_000_000) == Decimal("12")
    with_cache = _model("2.00", "12.00", "0.20")
    assert prices.cost_usd(with_cache, 1_000_000, 0, cached_tokens=500_000) == Decimal(
        "1.100000"
    )
    no_cache_price = _model("2.00", "12.00")
    assert prices.cost_usd(no_cache_price, 1_000_000, 0, cached_tokens=500_000) == 2
    assert prices.cost_usd(_model("2.00", "12.00"), 7, 3) == Decimal("0.000050")


def test_no_price_is_none():
    assert prices.cost_usd(_model(), 100, 100) is None
    assert prices.cost_usd(None, 100, 100) is None


@override_settings(
    TRIPAULX={"AI_PRICE_OVERRIDES": {"openai:m": {"input": "1", "output": "3"}}}
)
def test_settings_override_wins_over_catalog():
    assert prices.cost_usd(_model("2.00", "12.00"), 1_000_000, 1_000_000) == 4
    assert prices.prices_for(_model()).input == Decimal("1")


def _agent(instructions="Be the reviewer.", template="{context}\n{input}"):
    return SimpleNamespace(instructions=instructions, input_template=template)


def _version(name, number, text):
    return SimpleNamespace(
        skill=SimpleNamespace(name=name), number=number, instructions=text
    )


def test_layers_in_order_with_headers():
    text = prompt.build_instructions(
        _agent(),
        [_version("Style", 2, "Be formal."), _version("Privacy", 1, "No IDs.")],
        overlay="Document 42",
        output_schema={"type": "object"},
    )
    marks = [
        text.index(DEFAULT_BASE_PROMPT),
        text.index("--- AGENT IDENTITY AND RULES ---"),
        text.index("--- SKILL: Style (v2) ---"),
        text.index("--- SKILL: Privacy (v1) ---"),
        text.index("--- CONTEXT OF THIS CALL ---"),
        text.index("--- OUTPUT FORMAT ---"),
    ]
    assert marks == sorted(marks)
    assert '"type": "object"' in text


@override_settings(TRIPAULX={"AI_BASE_PROMPT": "Acme voice."})
def test_base_prompt_comes_from_settings_and_empty_layers_are_skipped():
    assert prompt.build_instructions(_agent(instructions="  "), []) == "Acme voice."
    with override_settings(TRIPAULX={"AI_BASE_PROMPT": ""}):
        assert prompt.build_instructions(_agent(instructions=" "), []) == ""


def test_input_template():
    assert prompt.build_input(_agent(), "DOC", context="CTX") == "CTX\nDOC"
    assert prompt.build_input(_agent(template="{foo} {input}"), "X") == "{foo} X"
    assert prompt.build_input(_agent(template="{input}"), "v {x} {y}") == "v {x} {y}"
    briefed = prompt.build_input(_agent(template="{input}"), "X", brief="### A\nnote")
    assert briefed.endswith(f"{prompt.BRIEF_HEADER}\n### A\nnote")
    assert prompt.render_template("{input", input="X") == "{input"


def test_template_complaints():
    assert "{input}" in prompt.template_complaint("{context}")
    assert prompt.template_complaint("{input} {") is not None
    assert prompt.template_complaint("{context}\n\n{input}") is None
