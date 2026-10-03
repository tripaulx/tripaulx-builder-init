# Generated project reference

## Layout

| Path | What |
|---|---|
| `config/settings/base_parts/` | Settings chunks. `base.py` only re-exports them; edit a chunk, never `base.py`. |
| `config/settings/base_parts/apps.py` | `PROJECT_SHARED_APPS` / `PROJECT_TENANT_APPS`: put new business apps here. |
| `config/settings/base_parts/tripaulx.py` | The `TRIPAULX` options dict, fed by the `APP_*` environment variables. |
| `config/settings/{local,prod,test}.py` | Per-environment settings. `prod.py` fails fast on unsafe configuration. |
| `config/urls.py` / `urls_public.py` | Workspace routes / public-schema (apex domain) routes. |
| `users/` | The concrete `User` (inherits `tripaulx.accounts.models.AbstractTripaulxUser`). |
| `legal/` | Project overrides of the legal documents (see its README). |
| `tests/` | pytest + factory_boy. Use `tripaulx.core.testing.TenantTestCase` / `TenantAPITestCase`. |
| `start`, `pg` | Local setup, dev server and tests; local PostgreSQL helper. |
| `Dockerfile`, `entrypoint.sh`, `healthcheck.sh`, `captain-definition` | One image, `APP_ROLE=web` (gunicorn) or `worker` (`db_worker`). |
| `deploy`, `scripts/caprover-deploy.sh` | `./deploy prod [web\|worker\|all]`. |
| `docs/deployment.md` | Step-by-step CapRover guide (en; pt-BR in `docs/pt-BR/`). |

## Key environment variables

| Variable | Meaning |
|---|---|
| `SECRET_KEY` | Django secret (required in production). |
| `APP_BASE_DOMAIN` | Apex domain; workspaces live at `<slug>.<APP_BASE_DOMAIN>`. |
| `APP_FIELD_ENCRYPTION_KEY` | Fernet key for encrypted fields (API keys, TOTP secrets). Required in production. |
| `APP_FILE_ENCRYPTION_KEY` | Master key for file encryption. Back it up: losing it loses every encrypted file. |
| `APP_SIGNUP_ENABLED` | Public sign-up that creates workspaces (on by default). |
| `APP_S3_*` | S3-compatible storage; off until both access keys are set. |
| `APP_AI_*` | AI limits and base prompt. Provider keys are stored per workspace through the API, never in env. |
| `APP_LEGAL_*` | Placeholders of the legal documents (company, DPO, jurisdiction...). |
| `MAIL_*` | SMTP fallback until Mailgun is configured in the public admin. |
| `DJANGO_TASKS_BACKEND` | `immediate` (default) or `database` (with the worker app). |

The full list is in `.env.example` (local) and `.env.prod.example` (production).

## SDK apps

`tripaulx.core`, `tripaulx.tenants`, `tripaulx.accounts`, `tripaulx.mail`,
`tripaulx.storage`, `tripaulx.ai` (+ `tripaulx.ai.catalog`) and `tripaulx.legal`.
Their Django labels are `tpsdk_*`. The guides are in the repository's `docs/` folder:
https://github.com/tripaulx/tripaulx-builder-init/tree/main/docs
