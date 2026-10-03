"""OpenAI calls: parsing, error classification, JSON and web sources."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import openai
import pytest

from tripaulx.ai.catalog.models import AIModel
from tripaulx.ai.providers import AIRequest
from tripaulx.ai.providers.openai_responses import OpenAIClient

from .helpers import (
    openai_response,
    sdk_connection_error,
    sdk_error,
    sdk_timeout,
)

CLIENT = OpenAIClient()
DOCS = "docs.example.com"


def _request(**fields: object) -> AIRequest:
    model = AIModel(
        provider="openai", identifier="gpt-5.6-terra", supports_reasoning=True
    )
    base = {"model": model, "instructions": "sys", "input": "user", "api_key": "sk-x"}
    base.update(fields)
    return AIRequest(**base)


def _call(request: AIRequest, **patch: object):
    with mock.patch.object(OpenAIClient, "send", **patch) as send:
        return CLIENT.call(request), send


def test_success_reads_text_usage_and_model():
    raw = openai_response(
        "answer", input_tokens=10, output_tokens=5, cached=2, reasoning=3
    )
    r, send = _call(_request(), return_value=raw)
    assert r.ok and r.text == "answer"
    assert (r.input_tokens, r.output_tokens, r.total_tokens) == (10, 5, 15)
    assert (r.cached_tokens, r.reasoning_tokens) == (2, 3)
    assert r.responded_model == "gpt-5.6-terra" and r.http_status == 200
    api_key, params, timeout = send.call_args.args
    assert api_key == "sk-x" and params["instructions"] == "sys" and timeout == 120.0


@pytest.mark.parametrize(
    ("exc", "code", "http"),
    [
        (sdk_error(openai, 401, "Incorrect API key"), "key_rejected", 401),
        (sdk_error(openai, 403), "no_permission", 403),
        (sdk_error(openai, 404), "unknown_model", 404),
        (sdk_error(openai, 429), "rate_limited", 429),
        (sdk_error(openai, 400, "Unsupported parameter"), "bad_request", 400),
        (sdk_error(openai, 503), "provider_unavailable", 503),
        (sdk_timeout(openai), "timeout", None),
        (sdk_connection_error(openai), "no_connection", None),
        (RuntimeError("x"), "unexpected_error", None),
    ],
)
def test_sdk_errors_become_codes(exc, code, http):
    r, _ = _call(_request(), side_effect=exc)
    assert not r.ok
    assert r.error.code == code
    assert r.http_status == http


def test_detail_carries_the_provider_message():
    r, _ = _call(_request(), side_effect=sdk_error(openai, 401, "Incorrect API key"))
    assert "Incorrect API key" in r.error.detail
    assert "OpenAI rejected the API key" in r.error.message


def test_incomplete_answer():
    r, _ = _call(
        _request(), return_value=openai_response("part", incomplete="max_output_tokens")
    )
    assert not r.ok and r.error.code == "incomplete_response" and r.text == "part"


def test_json_valid_and_invalid():
    schema = {"type": "object"}
    r, _ = _call(
        _request(output_schema=schema), return_value=openai_response('{"ok": true}')
    )
    assert r.ok and r.data == {"ok": True}
    r, _ = _call(
        _request(output_schema=schema), return_value=openai_response("not json")
    )
    assert not r.ok and r.error.code == "invalid_json"


def test_key_outside_latin1_is_never_sent():
    r, send = _call(_request(api_key="sk-proj-aaaМbbb"))
    send.assert_not_called()
    assert r.error.code == "invalid_key"
    assert "U+041C" in r.error.message and "position 12" in r.error.message


def test_missing_sdk_is_a_clear_error():
    from tripaulx.ai.providers import ProviderNotInstalled

    r, _ = _call(_request(), side_effect=ProviderNotInstalled("openai"))
    assert r.error.code == "provider_missing"
    assert "tripaulx-sdk[openai]" in r.error.message


def test_sources_are_unique_https_and_on_the_allowed_domains():
    raw = openai_response("Findings")
    notes = [
        {"url": f"https://{DOCS}/1/", "title": "Guide"},
        {"url": f"https://{DOCS}/1/", "title": "Guide"},
        {"url": "https://other.example.org/x", "title": "Other"},
        {"url": f"http://{DOCS}/9/", "title": "Plain http"},
    ]
    raw.output = [SimpleNamespace(type="web_search_call")] * 2 + [
        SimpleNamespace(
            type="message",
            content=[
                SimpleNamespace(
                    annotations=[
                        SimpleNamespace(type="url_citation", **n) for n in notes
                    ]
                )
            ],
        )
    ]
    r, _ = _call(_request(web_search=True, search_domains=(DOCS,)), return_value=raw)
    assert r.sources == ({"url": f"https://{DOCS}/1/", "title": "Guide"},)
    assert r.web_searches == 2
