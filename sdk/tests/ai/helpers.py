"""Shared doubles of the AI tests (no network anywhere).

``openai_response``/``anthropic_response`` imitate the SDK objects (clients
only read attributes, so ``SimpleNamespace`` is enough). ``sdk_error`` builds
the typed SDK exception for an HTTP status. Tests replace the network seam,
``ProviderClient.send``.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import httpx2

from tripaulx.accounts.models import Role
from tripaulx.ai.catalog.models import AIModel
from tripaulx.ai.models import Agent, AgentRole, AISettings, Skill
from tripaulx.ai.providers.anthropic_messages import AnthropicClient
from tripaulx.ai.providers.openai_responses import OpenAIClient
from tripaulx.ai.services import keys
from tripaulx.ai.services import skills as skill_service
from tripaulx.core.testing import TenantAPITestCase

OPENAI_SEND = (OpenAIClient, "send")
ANTHROPIC_SEND = (AnthropicClient, "send")


def configure_ai(
    *,
    provider: str = "openai",
    identifier: str = "gpt-5.6-terra",
    reasoning: bool = True,
    prices: tuple[str, str] | None = ("2.00", "12.00"),
    enabled: bool = True,
    key: str | None = "sk-test-workspace-key",
) -> tuple[AISettings, AIModel]:
    """Leave the settings ready to run (model, key, enabled)."""
    model, _ = AIModel.objects.get_or_create(
        provider=provider, identifier=identifier, defaults={"label": identifier}
    )
    model.active = True
    model.supports_reasoning = reasoning
    model.input_price_usd_1m = Decimal(prices[0]) if prices else None
    model.output_price_usd_1m = Decimal(prices[1]) if prices else None
    model.cached_price_usd_1m = None
    model.save()
    settings = AISettings.load()
    settings.enabled = enabled
    settings.provider = provider
    settings.model_identifier = identifier
    settings.save()
    if key:
        keys.add(provider, key, by=None)
    return AISettings.load(), model


def openai_response(
    text: str = "ok",
    *,
    model: str = "gpt-5.6-terra",
    input_tokens: int = 100,
    output_tokens: int = 20,
    cached: int = 0,
    reasoning: int = 0,
    incomplete: str | None = None,
) -> SimpleNamespace:
    """Build the Responses API object, reduced to what the client reads."""
    usage = SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        input_tokens_details=SimpleNamespace(cached_tokens=cached),
        output_tokens_details=SimpleNamespace(reasoning_tokens=reasoning),
    )
    response = SimpleNamespace(
        id="resp_123",
        model=model,
        output_text=text,
        usage=usage,
        incomplete_details=SimpleNamespace(reason=incomplete) if incomplete else None,
    )
    response.model_dump = lambda mode="json": {"id": "resp_123", "model": model}
    return response


def anthropic_response(
    text: str = "ok",
    *,
    model: str = "claude-sonnet-5-5",
    input_tokens: int = 100,
    output_tokens: int = 20,
    cache_read: int = 0,
    cache_write: int = 0,
    thinking: int = 0,
    stop: str = "end_turn",
    citations: list[dict[str, Any]] | None = None,
    searches: int = 0,
) -> SimpleNamespace:
    """Build the Messages API object, reduced to what the client reads."""
    cites = [
        SimpleNamespace(type="web_search_result_location", **c) for c in citations or []
    ]
    return SimpleNamespace(
        id="msg_123",
        model=model,
        stop_reason=stop,
        stop_details=SimpleNamespace(category="cyber") if stop == "refusal" else None,
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=text, citations=cites),
        ],
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read,
            cache_creation_input_tokens=cache_write,
            output_tokens_details=SimpleNamespace(thinking_tokens=thinking),
            server_tool_use=SimpleNamespace(web_search_requests=searches),
        ),
    )


def _http(status: int, message: str) -> httpx2.Response:
    request = httpx2.Request("POST", "https://api.example.com/v1/call")
    return httpx2.Response(
        status, request=request, json={"error": {"message": message}}
    )


def sdk_error(module: Any, status: int, message: str = "provider error") -> Exception:
    """Build the typed SDK exception (``openai``/``anthropic``) for a status."""
    response = _http(status, message)
    return module.APIStatusError(message, response=response, body=response.json())


def sdk_timeout(module: Any) -> Exception:
    """Build the SDK timeout exception."""
    return module.APITimeoutError(request=httpx2.Request("POST", "https://example.com"))


def sdk_connection_error(module: Any) -> Exception:
    """Build the SDK connection exception."""
    return module.APIConnectionError(
        request=httpx2.Request("POST", "https://example.com")
    )


def new_agent(name: str, *, role: str = AgentRole.SPECIALIST, **fields: Any) -> Agent:
    """Create an agent with default instructions."""
    fields.setdefault("instructions", f"You are {name}.")
    return Agent.objects.create(name=name, role=role, **fields)


def published_skill(name: str, instructions: str = "Follow the rule.") -> Skill:
    """Create a skill with version 1 published."""
    skill = Skill.objects.create(name=name, instructions=instructions)
    skill_service.publish(skill, by=None)
    skill.refresh_from_db()
    return skill


class AITestCase(TenantAPITestCase):
    """Tenant API test case with an admin and a member of the workspace."""

    def setUp(self) -> None:
        super().setUp()
        self.admin = self.make_user(
            email="admin@example.com", role=Role.ADMIN, first_name="Ana"
        )
        self.member = self.make_user(email="member@example.com")
        self.admin_api = self.api_client(self.admin)
        self.member_api = self.api_client(self.member)
