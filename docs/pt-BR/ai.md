# IA: provedores, agentes, skills e uso

O `tripaulx.ai` dá a cada workspace as próprias configurações de IA, chaves
de provedor cifradas, agentes (sozinhos ou em equipe), skills versionadas e um
registro de uso com custo, tokens, latência e erros. O `tripaulx.ai.catalog`
guarda o catálogo compartilhado de modelos, com preços, no schema public.

Versão em inglês: [../ai.md](../ai.md).

## Instalar e ligar

```toml
# pyproject.toml: "ai" instala os dois SDKs; "openai" ou "anthropic", um só.
dependencies = ["tripaulx-sdk[storage,ai]"]
```

O `tripaulx.settings.apps` instala o `tripaulx.ai.catalog` (compartilhado) e
o `tripaulx.ai` (tenant). Os SDKs dos provedores só são importados na hora da
chamada: um SDK ausente vira o erro `provider_missing`, com o extra a instalar.

```python
# config/urls.py (workspaces)
urlpatterns += [path("api/v1/ai/", include("tripaulx.ai.api.urls"))]
```

O template de projeto traz o chunk de settings `base_parts/ai.py` (`APP_AI_*`).

## Configurações (`TRIPAULX`)

| Chave | Padrão | Significado |
|---|---|---|
| `AI_BASE_PROMPT` | texto neutro de assistente | Primeira camada de todo prompt de sistema. |
| `AI_PROVIDERS` | `{}` | Provedores extras: nome -> caminho de um `ProviderClient`. |
| `AI_ORIGINS` | `{}` | Origens de execução extras: valor -> rótulo. |
| `AI_TIMEOUT_S` | `120` | Uma chamada ao provedor. |
| `AI_RUN_DEADLINE_S` | `240` | Uma execução inteira; precisa caber no `GUNICORN_TIMEOUT` com execução imediata. |
| `AI_MAX_OUTPUT_TOKENS` | `32000` | Teto absoluto de tokens de saída por chamada. |
| `AI_MAX_INPUT_CHARS` / `AI_MAX_CONTEXT_CHARS` | `80000` / `20000` | Limites de tamanho do `run`. |
| `AI_BRIEF_LIMIT_CHARS` | `20000` | Quanto da equipe o próximo membro vê. |
| `AI_WEB_SEARCH_PRICE_USD` | `"0.01"` | Preço de uma pesquisa na internet, somado ao custo. |
| `AI_PRICE_OVERRIDES` | `{}` | `"provedor:identificador"` -> `{"input", "cached", "output"}` (USD/1M). |
| `AI_TEST_TIMEOUT_S` | `30` | A chamada de "testar IA". |

Escopos de throttle (em `tripaulx.settings.rest`): `ai_test` (6/min),
`ai_run` (10/min) e `ai_poll` (120/min).

## Provedores

`ProviderClient.call(AIRequest) -> AIResponse` nunca levanta exceção: toda
falha vira um `AIError` com `code` estável (`key_rejected`, `rate_limited`,
`timeout`, `invalid_json`, `refused`...), uma `message` traduzida e um
`detail` técnico. `classify_error(exc, request)` traduz exceções do SDK.

- **OpenAI** (`openai`): Responses API, `store=False`, esforço de raciocínio e
  verbosidade, piso de tokens de saída por esforço, `web_search` com domínios
  permitidos e saída em JSON Schema estrito.
- **Anthropic** (`anthropic`): Messages API. Modelos atuais recebem
  `output_config.effort` (o raciocínio é adaptativo); modelos marcados com
  `uses_thinking_budget` recebem `thinking.budget_tokens`. Saída JSON usa
  `output_config.format`; a pesquisa na internet é a ferramenta de servidor
  (versão em `options["web_search_tool"]`). `options["fallbacks"]` (semeado
  como `"default"` no Claude Opus 5.5 e no Sonnet 5.5) liga o fallback de
  recusa no servidor, pelo endpoint beta. Os tokens de entrada incluem leituras
  e escritas de cache.

Para registrar outro provedor, em tempo de execução ou nas settings:

```python
from tripaulx.ai import providers

providers.register("acme", "myproject.ai.AcmeClient")  # instância, classe ou caminho
providers.get_provider("acme")
```

## Catálogo compartilhado

O `AIModel` vive no schema public; os workspaces o referenciam por
`provider` + `identifier`. A migration `0002` semeia OpenAI (GPT-6 Luna, 6.1
Sol, Astra; família GPT-5.6; GPT-5, mini, nano) e Anthropic (Claude Opus 5.5,
Sonnet 5.5, Haiku 4.5) com preços, faixa de custo, destaque e recomendado. O
catálogo só é editado pelo admin do schema public. Para atualizar:

```bash
python manage.py ai_sync_catalog catalog.toml            # cria ou atualiza
python manage.py ai_sync_catalog prices.json --prices-only
```

As entradas usam os nomes de campo do `AIModel` (`provider` e `identifier`
obrigatórios); linhas existentes só recebem os campos informados.

## Models do workspace

- `AISettings`: singleton com `enabled`, `provider`, `model_identifier`,
  `effort`, `max_output_tokens`, `daily_cap_usd`, `store_content` e
  `retention_days`.
- `AIKey`: uma chave ativa **por provedor**, cifrada com
  `tripaulx.core.crypto`. Cadastrar uma chave encerra a anterior
  (`replaced`); excluir a encerra (`deleted`); a chave encerrada mantém a
  linha (quem e quando, com nomes congelados), mas o segredo é apagado.
- `Agent` (especialista ou coordenador com equipe ordenada), `Skill` com
  rascunho e `SkillVersion`s publicadas, e `AIEvent` (uma linha por chamada).

## Execuções

`tripaulx.ai.services.execution.run(agent, text, origin=..., ...)` devolve um
`RunResult` e nunca levanta. Um coordenador roda os especialistas em ordem
(cada um vê um resumo das respostas anteriores) e depois consolida; a execução
para no primeiro erro. Os parâmetros seguem skill > agente > configurações,
campo a campo; só skills publicadas participam. O teto diário é checado uma
vez por execução.

O prompt de sistema tem cinco camadas: prompt base, agente, skills
publicadas, a sobreposição do chamador e o esquema de saída. O template da
entrada aceita `{input}` e `{context}`.

A API roda os agentes como tarefas do `django.tasks`
(`tripaulx.ai.tasks.run_agent`): com o backend imediato, `run` responde 200
com o resultado; com fila, responde 202 e o cliente consulta
`executions/<task_id>/`. Uma execução com `store_content=False` guarda só
métricas, e a linha da fila é apagada quando o resultado é entregue.

As origens são um registro (`playground`, `test`, `api` e `other` vêm de
fábrica):

```python
from tripaulx.ai.services.origins import register_origin

register_origin("invoice", _("Invoice editor"))
```

## API (`/api/v1/ai/`)

| Rota | Quem |
|---|---|
| `GET settings/` / `PATCH settings/` | membros leem / proprietários e admins alteram |
| `GET key/` / `POST key/` `{provider, api_key}` / `DELETE key/?provider=` | membros leem a auditoria / admins alteram; a chave nunca volta |
| `GET providers/` | membros: catálogo por provedor, com cartões e preços |
| `POST test/` | admins: uma chamada de verdade; recusa do provedor é 200 com `ok: false` |
| `GET dashboard/` | membros |
| CRUD `agents/`, `POST agents/<id>/duplicate/` | membros leem / admins alteram |
| `POST agents/<id>/run/` `{input, context?}` | qualquer membro, throttle `ai_run` |
| CRUD `skills/`, `publish/`, `versions/`, `duplicate/` | membros leem / admins alteram |
| `GET events/`, `events/report/?days=7\|30\|90`, `events/recent/` | membros veem metadados; só admins recebem o conteúdo em `events/<id>/` |
| `GET executions/<task_id>/` | só quem iniciou a execução |

## Retenção

`retention_days` (padrão 90; 0 guarda para sempre) apaga prompt, entrada,
saída, resposta bruta e detalhe de erro dos eventos mais antigos; as métricas
ficam. Rode diariamente para todos os workspaces:

```bash
python manage.py ai_purge_content                 # todos os workspaces
python manage.py ai_purge_content --schema acme --days 30
```

ou enfileire a tarefa `tripaulx.ai.tasks.purge_ai_content` a partir de um
agendador. Com `django-tasks-db`, limpe também as linhas antigas de tarefas
com o comando dele.
