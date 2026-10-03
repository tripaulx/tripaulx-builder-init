"""OpenAI Responses API parameters per model family (pure, no network)."""

from __future__ import annotations

from decimal import Decimal

from django.test import override_settings

from tripaulx.ai.catalog.models import AIModel
from tripaulx.ai.providers import AIRequest
from tripaulx.ai.providers.common import (
    DEFAULT_OUTPUT_WITHOUT_REASONING,
    OUTPUT_FLOOR_BY_EFFORT,
    output_limit,
)
from tripaulx.ai.providers.openai_responses import OpenAIClient

CLIENT = OpenAIClient()
DOCS = "docs.example.com"


def _model(reasoning: bool = True, **fields: object) -> AIModel:
    return AIModel(
        provider="openai",
        identifier="gpt-5.6-terra",
        supports_reasoning=reasoning,
        **fields,
    )


def _request(**fields: object) -> AIRequest:
    base = {
        "model": _model(),
        "instructions": "sys",
        "input": "user",
        "api_key": "sk-x",
    }
    base.update(fields)
    return AIRequest(**base)


def test_reasoning_model_gets_effort_and_verbosity_never_temperature():
    p = CLIENT.build_params(
        _request(effort="low", verbosity="high", temperature=Decimal("0.5"))
    )
    assert p["reasoning"] == {"effort": "low"}
    assert p["text"]["verbosity"] == "high"
    assert "temperature" not in p
    assert p["store"] is False
    assert "user" not in p


def test_model_refusing_minimal_gets_low():
    model = _model(accepts_minimal_effort=False)
    request = _request(model=model, effort="minimal")
    assert CLIENT.build_params(request)["reasoning"] == {"effort": "low"}
    assert output_limit(request) == OUTPUT_FLOOR_BY_EFFORT["low"]


def test_model_accepting_minimal_keeps_it():
    assert CLIENT.build_params(_request(effort="minimal"))["reasoning"] == {
        "effort": "minimal"
    }


def test_model_without_reasoning_gets_temperature_only():
    p = CLIENT.build_params(
        _request(model=_model(False), effort="low", temperature=Decimal("0.5"))
    )
    assert p["temperature"] == 0.5
    assert "reasoning" not in p and "text" not in p


def test_output_floor_per_effort():
    assert (
        CLIENT.build_params(_request(effort="high", max_output_tokens=100))[
            "max_output_tokens"
        ]
        == 16000
    )
    assert CLIENT.build_params(_request())["max_output_tokens"] == 8000
    assert (
        CLIENT.build_params(_request(effort="low", max_output_tokens=9000))[
            "max_output_tokens"
        ]
        == 9000
    )


@override_settings(TRIPAULX={"AI_MAX_OUTPUT_TOKENS": 5000})
def test_hard_ceiling():
    assert CLIENT.build_params(_request(effort="high"))["max_output_tokens"] == 5000


def test_without_reasoning_uses_request_or_default():
    assert (
        CLIENT.build_params(_request(model=_model(False)))["max_output_tokens"]
        == DEFAULT_OUTPUT_WITHOUT_REASONING
    )
    assert (
        CLIENT.build_params(_request(model=_model(False), max_output_tokens=700))[
            "max_output_tokens"
        ]
        == 700
    )


def test_schema_becomes_strict_json_schema():
    p = CLIENT.build_params(
        _request(output_schema={"type": "object"}, schema_name="reviewer")
    )
    assert p["text"]["format"] == {
        "type": "json_schema",
        "name": "reviewer",
        "schema": {"type": "object"},
        "strict": True,
    }


def test_web_search_with_allowed_domains():
    p = CLIENT.build_params(_request(web_search=True, search_domains=(DOCS,)))
    assert p["tools"] == [
        {"type": "web_search", "filters": {"allowed_domains": [DOCS]}}
    ]
    assert CLIENT.build_params(_request(web_search=True))["tools"] == [
        {"type": "web_search"}
    ]
    assert "tools" not in CLIENT.build_params(_request())


def test_minimal_effort_rises_to_low_only_with_search():
    with_search = CLIENT.build_params(_request(web_search=True, effort="minimal"))
    without = CLIENT.build_params(_request(effort="minimal"))
    assert with_search["reasoning"] == {"effort": "low"}
    assert without["reasoning"] == {"effort": "minimal"}
