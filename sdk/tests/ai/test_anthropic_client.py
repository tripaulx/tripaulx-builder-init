"""Anthropic Messages API client: parameters, parsing and errors."""

from __future__ import annotations

from decimal import Decimal
from unittest import mock

import anthropic
import pytest

from tripaulx.ai.catalog.models import AIModel
from tripaulx.ai.providers import AIRequest
from tripaulx.ai.providers.anthropic_messages import (
    DEFAULT_WEB_SEARCH_TOOL,
    FALLBACK_BETA,
    AnthropicClient,
)

from .helpers import anthropic_response, sdk_connection_error, sdk_error, sdk_timeout

CLIENT = AnthropicClient()
DOCS = "docs.example.com"


def _model(**fields: object) -> AIModel:
    fields.setdefault("supports_reasoning", True)
    return AIModel(provider="anthropic", identifier="claude-sonnet-5-5", **fields)


def _request(**fields: object) -> AIRequest:
    base = {
        "model": _model(),
        "instructions": "sys",
        "input": "user",
        "api_key": "sk-ant",
    }
    base.update(fields)
    return AIRequest(**base)


def test_messages_shape_effort_and_no_sampling():
    p = CLIENT.build_params(_request(effort="high", temperature=Decimal("0.3")))
    assert p["system"] == "sys"
    assert p["messages"] == [{"role": "user", "content": "user"}]
    assert p["max_tokens"] == 16000
    assert p["output_config"] == {"effort": "high"}
    assert "thinking" not in p and "extra_body" not in p


def test_minimal_effort_is_sent_as_low():
    p = CLIENT.build_params(_request(effort="minimal"))
    assert p["output_config"] == {"effort": "low"}


def test_budget_models_map_effort_to_a_thinking_budget():
    request = _request(model=_model(uses_thinking_budget=True), effort="medium")
    p = CLIENT.build_params(request)
    assert p["thinking"] == {"type": "enabled", "budget_tokens": 4096}
    assert p["thinking"]["budget_tokens"] < p["max_tokens"]
    assert "output_config" not in p
    no_effort = CLIENT.build_params(_request(model=_model(uses_thinking_budget=True)))
    assert "thinking" not in no_effort


def test_model_without_reasoning_gets_temperature():
    p = CLIENT.build_params(
        _request(model=_model(supports_reasoning=False), temperature=Decimal("0.3"))
    )
    assert p["extra_body"] == {"temperature": 0.3}


def test_json_schema_output_and_web_search_tool():
    schema = {"type": "object", "properties": {}}
    p = CLIENT.build_params(
        _request(output_schema=schema, web_search=True, search_domains=(DOCS,))
    )
    assert p["output_config"]["format"] == {"type": "json_schema", "schema": schema}
    assert p["tools"] == [
        {
            "type": DEFAULT_WEB_SEARCH_TOOL,
            "name": "web_search",
            "max_uses": 5,
            "allowed_domains": [DOCS],
        }
    ]
    old = _model(options={"web_search_tool": "web_search_20250305"})
    assert (
        CLIENT.build_params(_request(model=old, web_search=True))["tools"][0]["type"]
        == "web_search_20250305"
    )


def test_fallbacks_option_uses_the_beta_endpoint():
    p = CLIENT.build_params(_request(model=_model(options={"fallbacks": "default"})))
    assert p["fallbacks"] == "default" and p["betas"] == [FALLBACK_BETA]


def _call(request: AIRequest, **patch: object):
    with mock.patch.object(AnthropicClient, "send", **patch) as send:
        return CLIENT.call(request), send


def test_usage_mapping_counts_cache_and_thinking():
    raw = anthropic_response(
        "answer",
        input_tokens=50,
        output_tokens=30,
        cache_read=40,
        cache_write=10,
        thinking=12,
    )
    r, _ = _call(_request(), return_value=raw)
    assert r.ok and r.text == "answer"
    assert (r.input_tokens, r.cached_tokens, r.output_tokens) == (100, 40, 30)
    assert (r.total_tokens, r.reasoning_tokens) == (130, 12)
    assert r.responded_model == "claude-sonnet-5-5"


def test_citations_and_search_count():
    cites = [
        {"url": f"https://{DOCS}/a", "title": "A"},
        {"url": "https://other.example.org/b", "title": "B"},
    ]
    raw = anthropic_response(citations=cites, searches=3)
    r, _ = _call(_request(web_search=True, search_domains=(DOCS,)), return_value=raw)
    assert r.sources == ({"url": f"https://{DOCS}/a", "title": "A"},)
    assert r.web_searches == 3


def test_stop_reasons():
    r, _ = _call(_request(), return_value=anthropic_response("cut", stop="max_tokens"))
    assert r.error.code == "incomplete_response" and r.incomplete_reason == "max_tokens"
    r, _ = _call(_request(), return_value=anthropic_response("", stop="refusal"))
    assert r.error.code == "refused" and r.error.detail == "cyber"
    r, _ = _call(
        _request(output_schema={"type": "object"}),
        return_value=anthropic_response('{"a": 1}'),
    )
    assert r.ok and r.data == {"a": 1}


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (sdk_error(anthropic, 401), "key_rejected"),
        (sdk_error(anthropic, 429), "rate_limited"),
        (sdk_error(anthropic, 529), "provider_unavailable"),
        (sdk_timeout(anthropic), "timeout"),
        (sdk_connection_error(anthropic), "no_connection"),
    ],
)
def test_errors_are_classified(exc, code):
    r, _ = _call(_request(), side_effect=exc)
    assert r.error.code == code
    assert "Anthropic" in r.error.message
