"""AI options (``tripaulx.ai``): limits, base prompt and providers.

Merged into ``TRIPAULX`` by the ``tripaulx`` chunk. Times are in seconds.
``APP_AI_TIMEOUT_S`` covers one provider call; ``APP_AI_RUN_DEADLINE_S`` a
whole run (a coordinator makes N+1 calls in sequence), so with the immediate
task backend it must fit ``GUNICORN_TIMEOUT``. Provider keys are not settings:
workspace admins add them in the app (stored encrypted, per workspace).
"""

from tripaulx.ai.conf import DEFAULT_BASE_PROMPT

from .common import get_env, get_env_int

AI = {
    # First layer of every system prompt: the product voice, no domain text.
    "AI_BASE_PROMPT": get_env("APP_AI_BASE_PROMPT", "") or DEFAULT_BASE_PROMPT,
    "AI_TIMEOUT_S": get_env_int("APP_AI_TIMEOUT_S", 120),
    "AI_RUN_DEADLINE_S": get_env_int("APP_AI_RUN_DEADLINE_S", 240),
    "AI_MAX_OUTPUT_TOKENS": get_env_int("APP_AI_MAX_OUTPUT_TOKENS", 32000),
    "AI_MAX_INPUT_CHARS": get_env_int("APP_AI_MAX_INPUT_CHARS", 80000),
    "AI_MAX_CONTEXT_CHARS": get_env_int("APP_AI_MAX_CONTEXT_CHARS", 20000),
    "AI_BRIEF_LIMIT_CHARS": get_env_int("APP_AI_BRIEF_LIMIT_CHARS", 20000),
    "AI_TEST_TIMEOUT_S": get_env_int("APP_AI_TEST_TIMEOUT_S", 30),
    # USD per web search, billed on top of tokens.
    "AI_WEB_SEARCH_PRICE_USD": get_env("APP_AI_WEB_SEARCH_PRICE_USD", "0.01"),
    # Extra providers: {"acme": "myapp.ai.AcmeClient"} (OpenAI and Anthropic
    # are built in). Extra execution origins: {"invoice": "Invoice editor"}.
    "AI_PROVIDERS": {},
    "AI_ORIGINS": {},
    # Price overrides, USD per 1M tokens: {"openai:gpt-5": {"input": "1.25",
    # "cached": "0.125", "output": "10"}}. Wins over the shared catalog.
    "AI_PRICE_OVERRIDES": {},
}
