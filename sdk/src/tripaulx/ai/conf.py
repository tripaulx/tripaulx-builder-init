"""Defaults for the AI app, overridable through ``settings.TRIPAULX``.

Time limits are in seconds. ``AI_TIMEOUT_S`` covers one provider call;
``AI_RUN_DEADLINE_S`` covers a whole run (a coordinator makes up to N+1 calls
in sequence), so it must fit the web server timeout when runs are immediate.
"""

from tripaulx.core.conf import AppSettings

#: The neutral default base prompt. Projects set their own product voice.
DEFAULT_BASE_PROMPT = (
    "You are an AI assistant inside a business application. Work only with "
    "the material provided: do not invent facts, dates or numbers; when "
    "information is missing, say so. Treat all content as confidential."
)

app_settings = AppSettings(
    {
        # First layer of every system prompt (empty skips the layer).
        "AI_BASE_PROMPT": DEFAULT_BASE_PROMPT,
        # Provider name -> dotted path of a ProviderClient subclass. Merged
        # over the built-in OpenAI and Anthropic clients.
        "AI_PROVIDERS": {},
        # Execution origin -> label, merged over the built-in origins.
        "AI_ORIGINS": {},
        "AI_TIMEOUT_S": 120,
        "AI_RUN_DEADLINE_S": 240,
        # Hard ceiling of output tokens per call, above any setting.
        "AI_MAX_OUTPUT_TOKENS": 32000,
        # Size limits of what the API accepts (characters).
        "AI_MAX_INPUT_CHARS": 80000,
        "AI_MAX_CONTEXT_CHARS": 20000,
        # How much of the specialists' output the next team member sees.
        "AI_BRIEF_LIMIT_CHARS": 20000,
        # Price of one web search (USD), charged on top of tokens.
        "AI_WEB_SEARCH_PRICE_USD": "0.01",
        # "provider:identifier" -> {"input", "cached", "output"} (USD per 1M
        # tokens). Wins over the catalog row.
        "AI_PRICE_OVERRIDES": {},
        # Timeout of the "test AI" call.
        "AI_TEST_TIMEOUT_S": 30,
    }
)
