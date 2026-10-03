# Deploy

> English: [../deployment.md](../deployment.md)

Os projetos gerados a partir de `template/` fazem deploy no
[CapRover](https://caprover.com). O passo a passo completo vai junto com cada
projeto, renderizado com as respostas dele:
[`template/docs/pt-BR/deployment.md.jinja`](../../template/docs/pt-BR/deployment.md.jinja)
(inglês: [`template/docs/deployment.md.jinja`](../../template/docs/deployment.md.jinja)).

## Resumo

- **Uma imagem, dois papéis.** O `template/Dockerfile` builda uma imagem única
  `python:3.13-slim` (uv, `uv sync --frozen --no-dev`, usuário não root,
  `collectstatic` no build, `HEALTHCHECK`). `APP_ROLE=web` sobe o gunicorn;
  `APP_ROLE=worker` sobe o `manage.py db_worker` do `django.tasks`.
- **Quatro apps no CapRover por projeto:** `<slug>` (web), `<slug>-worker`,
  PostgreSQL e Redis (one-click apps).
- **Boot:** o `entrypoint.sh` confere as variáveis obrigatórias, espera o banco
  e roda `migrate_schemas --shared`, `bootstrap_workspace` e `migrate_schemas`
  (por padrão só no web, via `RUN_MIGRATIONS`).
- **Deploy:** `./deploy prod [web|worker|all]` roda o `scripts/check.sh`
  (ruff + pytest; pule com `SKIP_CHECKS=1`) e depois o
  `scripts/caprover-deploy.sh` empacota o projeto e envia com os tokens por app
  do `.env.deploy`.
- **Variáveis:** o `.env.prod.example` lista todas as variáveis de runtime
  lidas pelo código; o `.env.deploy.example`, as de deploy.
- **Subdomínios curinga** (`<slug>.<APP_BASE_DOMAIN>`), configurados uma vez:
  - registro `A *` proxied na Cloudflare, com SSL em Full (strict);
  - certificado Cloudflare Origin CA para `*.domínio` + apex no host do CapRover;
  - bloco `server_name *.domínio`, com guarda, no template nginx do app web.
- **Limites:** o código nunca chama a API do CapRover, e a senha do CapRover
  nunca entra no ambiente de nenhum app.

## CI

O job `deploy` do `.github/workflows/ci.yml` renderiza o template, copia o SDK
local para dentro do exemplo (o SDK ainda não está no PyPI), roda
`docker build` e o `shellcheck` em todos os scripts shell do template.
