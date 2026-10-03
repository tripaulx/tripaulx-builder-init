# Plano — `tripaulx-builder-init`

Base open source (GitHub + PyPI) para todos os projetos tripaulx-builders. É **só backend**
(API + admin) e sai pronta para deploy no CapRover.

---

## 1. Arquitetura: SDK + template

```
tripaulx-builder-init/              (monorepo público no GitHub)
├── sdk/       → pacote PyPI `tripaulx-sdk`; o projeto importa `tripaulx.*`
├── template/  → template Copier; o projeto nasce daqui
└── example/   → projeto gerado pelo template (fora do git); a CI roda tudo contra ele
```

- **SDK.** Reúne o que é igual em todo projeto: tenants, contas, mail, storage, IA, legal e core. Cada projeto instala o pacote e o atualiza com `uv lock --upgrade-package tripaulx-sdk`.
- **Template.** Reúne o que muda por projeto: settings, o `User` concreto, as apps de domínio, o Dockerfile, o deploy, a CI e o `.env`. Projeto novo: `copier copy --trust gh:tripaulx/tripaulx-builder-init meu-projeto`.
- **Fora do escopo agora:** frontend, cliente TypeScript e telas. O SDK expõe a API (OpenAPI via drf-spectacular) e o Django admin.

### Apps do SDK

| App (`label`) | Conteúdo |
|---|---|
| `tripaulx.core` (`tpsdk_core`) | BaseModel (UUID, soft delete), crypto Fernet, `TenantTestCase`, filtro de log, healthz, `AppSettings` |
| `tripaulx.tenants` (`tpsdk_tenants`) | `Workspace` (TenantMixin), `Domain`, `bootstrap_workspace`, criação de workspace pelo signup, convites |
| `tripaulx.accounts` (`tpsdk_accounts`) | `AbstractTripaulxUser`, signup, login com 2FA obrigatório, TOTP, passkeys, recuperação, dispositivos confiáveis, reset, JWT preso ao tenant |
| `tripaulx.mail` (`tpsdk_mail`) | config Mailgun cifrada, backend, templates de e-mail que o projeto pode sobrescrever |
| `tripaulx.storage` (`tpsdk_storage`) | S3 compatível, cifra envelope AES-GCM, chaves escopadas por tenant, política de tipos configurável |
| `tripaulx.ai` (`tpsdk_ai`) | provedores, chaves, catálogo, agentes, skills, eventos, orçamento, relatório, painel, testar |
| `tripaulx.legal` (`tpsdk_legal`) | catálogo + markdown sanitizado + permissão + API, modelos de documento, termos e privacidade |

**Labels: `tpsdk_*`** (`tpsdk_core`, `tpsdk_tenants`, `tpsdk_accounts`...).
- Um prefixo curto e exclusivo evita colisão com apps do projeto que se chamem `core`, `accounts`, `ai` etc., ou que já usem o prefixo `tripaulx_`.
- O import continua sendo `tripaulx.*`. Só o label do Django muda (`AppConfig.label`), e isso mexe nos nomes das tabelas.

### Template (o que fica no projeto)

```
<projeto>/
├── config/settings/{base,local,prod,test}.py   # curtos: usam os helpers do SDK
├── config/settings/base_parts/                 # settings em pedaços
├── config/urls.py · urls_public.py             # incluem tripaulx.*.urls
├── users/models.py                             # class User(AbstractTripaulxUser)
├── Dockerfile · captain-definition · entrypoint.sh · healthcheck.sh   (Fase 5)
├── deploy · scripts/caprover-deploy.sh                                (Fase 5)
├── pg · start
├── .env.example
└── CLAUDE.md · README.md
```

---

## 2. Contratos do SDK (para nenhum projeto precisar de fork)

1. **Configuração:** um único dict `TRIPAULX = {...}`. Cada app declara seus defaults em `conf.py` com `AppSettings`, e as envs do template alimentam esse dict.
   - Marca: `APP_NAME`, logo, remetente.
   - Auth: TTLs de código, issuer TOTP, RP do WebAuthn, signup on/off.
   - IA: prompt base, limites, preço da busca web.
   - Legal: schema e domínios de e-mail permitidos.
2. **Helpers de settings** (`tripaulx.settings`): listas de apps, middleware, logging, hosts e carga do `.env`. Na Fase 1 entram `rest_framework()` e `simple_jwt()`.
3. **User trocável:** o SDK traz o `AbstractTripaulxUser` (e-mail como login, `email_verified`, `password_login_disabled`, `role`) e o projeto define o model concreto. As migrations do SDK apontam para `settings.AUTH_USER_MODEL`.
4. **Registros de extensão:**
   - provedores de IA (`tripaulx.ai.providers.register`);
   - origens de execução de IA;
   - documentos legais.
5. **Signals:** `workspace_created`, `user_signed_up`, `user_logged_in_2fa`, `ai_call_finished`.
6. **Templates sobrescrevíveis:** os e-mails ficam em `templates/tripaulx/mail/*.html`.
7. **i18n:** tudo em inglês, com as mensagens em `gettext` e o locale `pt_BR` completo incluído no pacote (ver §11).
8. **Semver:** migrations compatíveis dentro de uma versão minor, CHANGELOG obrigatório e avisos de depreciação por uma versão minor antes de remover algo.

---

## 3. Stack

- Python ≥ 3.12 (a CI testa 3.12 e 3.13). Postgres 16/17. Redis em produção.
- **Django 6.1.1**, com 6.0 também suportado. **django-tenants 3.14.0** já declara `django<6.2`, então não precisa de override.
- **E-mail:** o Django 6.1 deprecou `EMAIL_BACKEND` em favor de `MAILERS`. Por isso o template usa `MAILERS` e exige Django ≥ 6.1.
- DRF, simplejwt + blacklist, drf-spectacular, cors-headers, whitenoise, gunicorn e psycopg 3.
- webauthn, qrcode, cryptography, nh3, boto3, pillow, django-simple-history e django-tasks-db (`django.tasks` nativo).
- IA: `openai` e `anthropic` como **extras** (`tripaulx-sdk[openai,anthropic]`).
- Build e dependências com `uv` (lock usado de fato no Docker e na CI). Publicação com hatchling.
- Dev: ruff, pytest, pytest-django, factory_boy.

---

## 4. Contas e tenants

**Funcionalidades:**
- Código de 6 dígitos por e-mail: guardado em hash, com TTL, limite de tentativas e cooldown.
- 2FA sempre ativo: por TOTP se o aplicativo autenticador estiver ligado, senão por e-mail.
- TOTP próprio, testado contra os vetores da RFC 6238, com anti-replay e QR em SVG.
- Passkeys (WebAuthn): login sem digitar e-mail e a opção "entrar somente com passkey".
  - Ela só vale com ao menos uma passkey cadastrada.
  - A última passkey não pode ser removida enquanto a opção estiver ligada.
- Códigos de recuperação, dispositivo confiável e reset de senha por código, com mensagens anti-enumeração.
- JWT com claim `schema`, para o token de um tenant não valer em outro.
- Throttles por escopo.
- **Signup cria workspace.**
  - No schema public, `POST /api/auth/signup/` cria o `Workspace` + `Domain`, migra o schema, cria o owner dentro dele e envia o código de verificação.
  - A operação é idempotente e protegida por `TRIPAULX["SIGNUP_ENABLED"]` e pelo throttle `auth_register`.
  - Criar um schema demora: medir na Fase 1 e, se passar de ~2 s, mover para `django.tasks`.
- **Papéis e convites.**
  - `role` com os valores owner, admin e member. Ele é o portão de admin do workspace, no lugar do `is_staff`.
  - Convite por e-mail com token de uso único. Endpoints de membros: listar, trocar papel, remover.
- Login por passkey também exige e-mail verificado.
- Endpoints de conta: trocar a senha logado, listar e revogar dispositivos confiáveis, renomear passkey.
- E-mails em templates, não em HTML dentro do Python.
- Challenge do WebAuthn no Redis em produção (obrigatório com mais de um worker).

---

## 5. IA (`tripaulx.ai`)

- **Models:**
  - `AISettings`: singleton por tenant, com liga/desliga, provedor, modelo, esforço e teto diário.
  - `AIKey`: cifrada, uma ativa **por provedor**, com histórico "cadastrada em… por…", substituir e excluir.
  - `Agent`: especialista ou coordenador, com equipe.
  - `Skill` + `SkillVersion`: rascunho e versões publicadas.
  - `AIEvent`: custo, tokens, latência e erro.
- **API:**
  - `settings/`, `key/`, `providers/`, `test/`, `dashboard/`;
  - `agents/`, `skills/`, `events/` (com as ações `report` e `recent`), `executions/<id>/`.
  - Isso cobre as abas Dashboard, Agentes, Novo agente, Skills, Relatório e Provedor e chave.

**Requisitos:**
1. **Interface de provedor.**
   - `ProviderClient.call(AIRequest) -> AIResponse` e `classify_error()`, escolhidos por registro.
   - Implementações: OpenAI (Responses API) e Anthropic (Messages API).
2. **Catálogo de modelos no schema public.**
   - Seed com os modelos atuais da OpenAI e da Anthropic, com preços e faixa de custo.
   - Comando `ai_sync_catalog` para atualizar preços.
   - Override de preço por settings.
3. **Prompt base vem de configuração**, sem texto de domínio no pacote.
4. As origens de execução viram um registro configurável pelo projeto.
5. **Segurança:**
   - config e chave só podem ser alteradas por owner ou admin;
   - o conteúdo dos eventos só pode ser lido por admin.
6. **Retenção:** comando e task `ai_purge_content` usando os dias de retenção configurados.
7. Migrations limpas: uma `0001` e um seed do catálogo.

---

## 6. Legal (`tripaulx.legal`)

- **Mecanismo:**
  - catálogo com whitelist e proteção contra path traversal;
  - markdown com várias camadas de sanitização (nh3);
  - permissão configurável por schema e domínios de e-mail permitidos;
  - API de lista e detalhe com `no-store`.
- **Fontes de documento:**
  - o pacote traz **modelos genéricos** com placeholders: matriz de riscos, plano de resposta a incidentes, registro de incidentes, inventário de dados, plano de arquitetura, termos de uso e política de privacidade;
  - o projeto aponta `TRIPAULX["LEGAL_CONTENT_DIRS"]` para o próprio `legal/` versionado no git;
  - os documentos do projeto têm prioridade sobre os modelos.
- Termos e privacidade ficam num endpoint **público**. Os documentos de governança ficam na área restrita.
- Os modelos nunca contêm nomes, contatos ou dados reais.

---

## 7. Deploy (template, CapRover)

- **Dockerfile:** estágio único `python:3.13-slim`, `uv sync --frozen`, `collectstatic` no build e `HEALTHCHECK`. O SDK vem do PyPI público, então o build não precisa de token.
- **entrypoint.sh:**
  - `APP_ROLE=web|worker`, espera o DB.
  - `migrate_schemas --shared`, `bootstrap_workspace`, `migrate_schemas`.
  - Depois gunicorn (web) ou `db_worker` (worker).
- **healthcheck.sh:** `HEALTHCHECK_HOST` vem da env.
- **`./deploy prod [web|worker|all]`** + `scripts/caprover-deploy.sh` + `.env.deploy.example`.
- Por projeto, quatro apps no CapRover: `<slug>`, `<slug>-worker`, Postgres e Redis. O passo a passo fica em `docs/deployment.md`.
- `.env.example` **completo**, com todas as variáveis lidas pelo código.
- **Domínio por workspace: subdomínio** (`<slug>.<APP_BASE_DOMAIN>`).
  - **Infra, configurada uma vez por projeto e documentada no template:**
    - registro DNS `A *` no Cloudflare, proxied, com SSL em Full (strict);
    - certificado **Cloudflare Origin CA** para `*.<domínio>` + apex, guardado no host CapRover;
    - um bloco `server_name *.<domínio>` no template nginx da web app no CapRover.
  - **O código nunca chama a API do CapRover.** A senha do CapRover nunca entra no env da app.
  - Já implementado no SDK:
    - slugs reservados;
    - regex de slug `^[a-z][a-z0-9_]{2,29}$`;
    - `/healthz` respondido **antes** da resolução do tenant;
    - `ALLOWED_HOSTS` com `.<domínio>`;
    - `SHOW_PUBLIC_IF_NO_TENANT_FOUND=False`.
  - **Domínio próprio do cliente** (Cloudflare for SaaS custom hostnames): fica **para depois do 0.1**.

---

## 8. Open source

- O repositório não contém dados, segredos, nomes de clientes, pessoas, projetos internos nem infraestrutura privada.
- A CI roda `gitleaks` em todo push.
- Arquivos do repositório:
  - `LICENSE`;
  - `README` com quickstart;
  - `SECURITY.md` (canal de reporte de vulnerabilidade);
  - `CONTRIBUTING.md`;
  - `CHANGELOG.md`;
  - `CODE_OF_CONDUCT.md`;
  - templates de issue e PR.
- **CI pública:**
  - ruff + pytest do SDK em matriz: Python 3.12/3.13 × Django 6.0/6.1 × Postgres 16/17;
  - renderizar o template com Copier e rodar os testes do projeto gerado de ponta a ponta;
  - `gitleaks`.
- **Release:**
  - tag `vX.Y.Z` dispara o build e o PyPI **Trusted Publishing** (OIDC, sem token guardado);
  - o template fica fixado em `tripaulx-sdk>=X.Y,<X+1`.
- Reservar o nome `tripaulx-sdk` no PyPI cedo.

---

## 9. Fases

| Fase | Entrega | Pronto quando |
|---|---|---|
| 0 ✅ | Monorepo, empacotamento (`sdk/pyproject`), `tripaulx.core`, `tenants`, `AbstractTripaulxUser`, helpers de settings, `template/` mínimo, `example/`, CI com matriz, arquivos de open source | `copier copy` gera o projeto; `migrate_schemas` + `bootstrap_workspace` rodam; `/healthz/` responde no public e no tenant |
| 1 ✅ | `accounts` + `mail` + signup de workspace + papéis e convites + doc do subdomínio (Cloudflare + CapRover) | signup → verify → login 2FA → TOTP → passkey → convite funcionam de ponta a ponta, com testes |
| 2 ✅ | `storage` | testes de cifra e de isolamento por tenant |
| 3 ✅ | `ai` + OpenAI + Anthropic + catálogo compartilhado | testes verdes; "Testar IA" funciona nos dois provedores |
| 4 ✅ | `legal` com modelos + termos/privacidade públicos | testes de XSS e de permissão |
| 5 ✅ | Deploy pelo template | imagem construída e testada (web + worker) na CI e localmente; **deploy real num servidor CapRover ainda pendente** |
| 6 | Release `0.1.0` no PyPI + docs | projeto novo do zero: `copier copy` → `./start` → `./deploy prod all`, sem editar nada à mão |

Cada funcionalidade entra junto com seus testes.

**Depois do 0.1** (fora do escopo agora): cliente TS gerado do OpenAPI (`@tripaulx/sdk`), kit de frontend, Gemini, domínio próprio do cliente.

---

## 10. Padrões de código

Registrados em **`CLAUDE.md`** na raiz:
- PEP 8 (ruff check + format, linha 88), docstrings PEP 257 e type hints.
- Arquivos com cerca de 150 linhas. **Acima de 300 a CI falha**.
- Layout modular por app: `models/` (um arquivo por model), `api/{serializers,views}/`, `services/`, `validators/`, `tasks/`, `admin/`, `tests/`.
- Lógica de negócio só em `services/`, sem duplicar regras entre validators, serializers e services.
- Settings divididas em `base_parts/`.
- Testes com pytest + factory_boy, menos de 150 linhas por arquivo.
- Migrations nunca removem campo sem confirmação.
- Comandos sempre com `uv run`.

Na CI entram `ruff check`, `ruff format --check`, um checador de tamanho de arquivo, um checador de docstrings (`ruff` regra `D`, convenção pep257) e a checagem de traduções.

## 11. Decisões

1. Signup cria workspace. Os usuários vivem no schema do tenant e têm `role`.
2. Provedores de IA: OpenAI + Anthropic.
3. Gerador: Copier.
4. Arquitetura SDK (PyPI) + template, **open source no GitHub** (`github.com/tripaulx/tripaulx-builder-init`).
5. Sem frontend no início: só API + admin.
6. Workspace por subdomínio, com wildcard Cloudflare + Origin CA + nginx no CapRover (ver §7).
7. **Idioma: 100% inglês, com versão pt-BR.**
   - Código, models, campos, endpoints, settings, commits e docs do SDK e do template ficam em inglês.
   - Tradução completa em `pt_BR` via gettext: mensagens da API, e-mails, labels e help texts do admin, e os modelos de documento legal.
   - Docs espelhadas em `docs/pt-BR/`, mais um `README.pt-BR.md`.
   - O template pergunta o idioma padrão do projeto (`LANGUAGE_CODE`, padrão `pt-br`).
   - A CI falha se houver string sem tradução.
8. Padrões de código do §10 (`CLAUDE.md`).
9. Licença **MIT**.
