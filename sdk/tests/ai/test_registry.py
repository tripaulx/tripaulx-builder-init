"""Provider and origin registries."""

from __future__ import annotations

from django.test import override_settings
import pytest

from tripaulx.ai import providers
from tripaulx.ai.providers import AIRequest, AIResponse, ProviderClient
from tripaulx.ai.providers.anthropic_messages import AnthropicClient
from tripaulx.ai.providers.openai_responses import OpenAIClient
from tripaulx.ai.services import origins


class EchoClient(ProviderClient):
    name = "echo"
    label = "Echo"

    def build_params(self, request: AIRequest) -> dict:
        return {"input": request.input}

    def send(self, api_key: str, params: dict, timeout_s: float) -> dict:
        return params

    def parse(self, raw: dict, request: AIRequest, *, latency_ms: int) -> AIResponse:
        return self.finish(request, text=raw["input"], latency_ms=latency_ms)

    def classify_sdk_error(self, exc, request):  # pragma: no cover - never raises
        raise AssertionError


@pytest.fixture
def _clean_registry():
    yield
    providers.unregister("echo")
    origins._registered.clear()


def test_builtins_are_registered():
    assert isinstance(providers.get_provider("openai"), OpenAIClient)
    assert isinstance(providers.get_provider("anthropic"), AnthropicClient)
    assert providers.get_provider("nope") is None
    assert providers.label_of("anthropic") == "Anthropic"
    assert providers.label_of("nope") == "nope"


@pytest.mark.usefixtures("_clean_registry")
def test_register_instance_class_or_path():
    for spec in (EchoClient(), EchoClient, "tests.ai.test_registry.EchoClient"):
        providers.register("echo", spec)
        client = providers.get_provider("echo")
        assert isinstance(client, EchoClient)
    assert ("echo", "Echo") in providers.choices()
    response = client.call(
        AIRequest(model=None, instructions="", input="hi", api_key="k")
    )
    assert response.ok and response.text == "hi"


@override_settings(
    TRIPAULX={"AI_PROVIDERS": {"echo": "tests.ai.test_registry.EchoClient"}}
)
def test_settings_add_providers():
    assert providers.names()[:2] == ["openai", "anthropic"]
    assert isinstance(providers.get_provider("echo"), EchoClient)


@pytest.mark.usefixtures("_clean_registry")
def test_runtime_registration_wins_over_builtins():
    providers.register("openai", EchoClient)
    try:
        assert isinstance(providers.get_provider("openai"), EchoClient)
    finally:
        providers.unregister("openai")
    assert isinstance(providers.get_provider("openai"), OpenAIClient)


@pytest.mark.usefixtures("_clean_registry")
def test_origins_registry():
    assert origins.is_valid("playground") and origins.is_valid("test")
    assert not origins.is_valid("invoice")
    origins.register_origin("invoice", "Invoice editor")
    assert origins.label("invoice") == "Invoice editor"
    with override_settings(TRIPAULX={"AI_ORIGINS": {"crm": "CRM"}}):
        assert origins.label("crm") == "CRM"
    assert origins.label("unknown") == "unknown"
