# AI: providers, agents, skills and usage

`tripaulx.ai` gives every workspace its own AI settings, encrypted provider
keys, agents (alone or as a team), versioned skills and a usage log with cost,
tokens, latency and errors. `tripaulx.ai.catalog` holds the shared model
catalog with prices in the public schema.

Portuguese version: [pt-BR/ai.md](pt-BR/ai.md).

## Install and wire

```toml
# pyproject.toml: "ai" installs both SDKs; "openai" or "anthropic" only one.
dependencies = ["tripaulx-sdk[storage,ai]"]
```

`tripaulx.settings.apps` installs `tripaulx.ai.catalog` (shared) and
`tripaulx.ai` (tenant). Provider SDKs are imported only when a call is made:
a missing SDK becomes the `provider_missing` error with the extra to install.

```python
# config/urls.py (workspaces)
urlpatterns += [path("api/v1/ai/", include("tripaulx.ai.api.urls"))]
```

The project template ships a `base_parts/ai.py` settings chunk (`APP_AI_*`).

## Settings (`TRIPAULX`)

| Key | Default | Meaning |
|---|---|---|
| `AI_BASE_PROMPT` | neutral assistant text | First layer of every system prompt. |
| `AI_PROVIDERS` | `{}` | Extra providers: name -> dotted path of a `ProviderClient`. |
| `AI_ORIGINS` | `{}` | Extra execution origins: value -> label. |
| `AI_TIMEOUT_S` | `120` | One provider call. |
| `AI_RUN_DEADLINE_S` | `240` | A whole run; fit it in `GUNICORN_TIMEOUT` when runs are immediate. |
| `AI_MAX_OUTPUT_TOKENS` | `32000` | Hard ceiling of output tokens per call. |
| `AI_MAX_INPUT_CHARS` / `AI_MAX_CONTEXT_CHARS` | `80000` / `20000` | Size limits of `run`. |
| `AI_BRIEF_LIMIT_CHARS` | `20000` | Team output the next member sees. |
| `AI_WEB_SEARCH_PRICE_USD` | `"0.01"` | Price of one web search, added to the cost. |
| `AI_PRICE_OVERRIDES` | `{}` | `"provider:identifier"` -> `{"input", "cached", "output"}` (USD/1M). |
| `AI_TEST_TIMEOUT_S` | `30` | The "test AI" call. |

Throttle scopes (in `tripaulx.settings.rest`): `ai_test` (6/min), `ai_run`
(10/min) and `ai_poll` (120/min).

## Providers

`ProviderClient.call(AIRequest) -> AIResponse` never raises: every failure is
an `AIError` with a stable `code` (`key_rejected`, `rate_limited`, `timeout`,
`invalid_json`, `refused`...), a translated `message` and a technical
`detail`. `classify_error(exc, request)` maps SDK exceptions to codes.

- **OpenAI** (`openai`): Responses API, `store=False`, reasoning effort and
  verbosity, an output-token floor per effort, `web_search` with allowed
  domains, strict JSON-schema output.
- **Anthropic** (`anthropic`): Messages API. Current models get
  `output_config.effort` (thinking is adaptive); models flagged
  `uses_thinking_budget` get `thinking.budget_tokens`. JSON output uses
  `output_config.format`; web search is the server tool (version in
  `options["web_search_tool"]`). `options["fallbacks"]` (seeded as `"default"`
  for Claude Opus 5.5 and Sonnet 5.5) turns on server-side refusal fallbacks
  through the beta endpoint. Input tokens include cache reads and writes.

Register another provider at runtime or in settings:

```python
from tripaulx.ai import providers

providers.register("acme", "myproject.ai.AcmeClient")  # instance, class or path
providers.get_provider("acme")
```

## Shared catalog

`AIModel` lives in the public schema; workspaces refer to it by
`provider` + `identifier`. Migration `0002` seeds OpenAI (GPT-6 Luna, 6.1 Sol,
Astra; GPT-5.6 family; GPT-5, mini, nano) and Anthropic (Claude Opus 5.5,
Sonnet 5.5, Haiku 4.5) with prices, cost tier, highlight and recommended
flags. The catalog is edited only from the public admin. Update it with:

```bash
python manage.py ai_sync_catalog catalog.toml            # create or update
python manage.py ai_sync_catalog prices.json --prices-only
```

Entries use the `AIModel` field names (`provider` and `identifier` required);
existing rows only get the fields given.

## Workspace models

- `AISettings`: singleton with `enabled`, `provider`, `model_identifier`,
  `effort`, `max_output_tokens`, `daily_cap_usd`, `store_content` and
  `retention_days`.
- `AIKey`: one active key **per provider**, encrypted with
  `tripaulx.core.crypto`. Adding a key closes the previous one (`replaced`);
  deleting closes it (`deleted`); a closed key keeps its row (who and when,
  with frozen names) but its secret is wiped.
- `Agent` (specialist or coordinator with an ordered team), `Skill` with draft
  and published `SkillVersion`s, and `AIEvent` (one row per call).

## Runs

`tripaulx.ai.services.execution.run(agent, text, origin=..., ...)` returns a
`RunResult` and never raises. A coordinator runs its specialists in order
(each sees a brief of the previous answers), then consolidates; the run stops
at the first error. Parameters resolve skill > agent > settings, field by
field; only published skills take part. The daily cap is checked once per run.

The system prompt has five layers: base prompt, agent, published skills, the
caller's overlay and the output schema. The input template accepts `{input}`
and `{context}`.

The API runs agents as `django.tasks` tasks (`tripaulx.ai.tasks.run_agent`):
with the immediate backend `run` answers 200 with the result; with a queue it
answers 202 and the client polls `executions/<task_id>/`. A run started with
`store_content=False` keeps only metrics, and its queue row is deleted once
the result is delivered.

Origins are a registry (`playground`, `test`, `api`, `other` built in):

```python
from tripaulx.ai.services.origins import register_origin

register_origin("invoice", _("Invoice editor"))
```

## API (`/api/v1/ai/`)

| Route | Who |
|---|---|
| `GET settings/` / `PATCH settings/` | members read / owners and admins write |
| `GET key/` / `POST key/` `{provider, api_key}` / `DELETE key/?provider=` | members read the audit state / admins write; the key is never returned |
| `GET providers/` | members: catalog grouped by provider with cards and prices |
| `POST test/` | admins: one real call; a provider refusal is a 200 with `ok: false` |
| `GET dashboard/` | members |
| `agents/` CRUD, `POST agents/<id>/duplicate/` | members read / admins write |
| `POST agents/<id>/run/` `{input, context?}` | any member, `ai_run` throttle |
| `skills/` CRUD, `publish/`, `versions/`, `duplicate/` | members read / admins write |
| `GET events/`, `events/report/?days=7\|30\|90`, `events/recent/` | members see metadata; only admins get the content on `events/<id>/` |
| `GET executions/<task_id>/` | only the user who started the run |

## Retention

`retention_days` (default 90; 0 keeps forever) clears the prompt, input,
output, raw response and error detail of older events; metrics stay. Run it
daily for every workspace:

```bash
python manage.py ai_purge_content                 # every workspace
python manage.py ai_purge_content --schema acme --days 30
```

or enqueue the `tripaulx.ai.tasks.purge_ai_content` task from a scheduler.
With `django-tasks-db`, also prune old task rows with its own command.
