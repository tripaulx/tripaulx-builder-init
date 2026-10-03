# tripaulx-builder-init

Open-source monorepo with two parts. The full plan is in `PLANO.md` (pt-BR).

- `sdk/`: the `tripaulx-sdk` package on PyPI, imported as `tripaulx.*`.
- `template/`: a Copier template for new projects.

Both are backend only: Django 6.1 + django-tenants, a DRF API and the Django admin, deployed on CapRover.

## Language
- Everything is written in **English**: code, identifiers, models, fields, endpoints, settings, docs and commits.
- pt-BR is a **translation**, not a source:
  - user-facing strings go through `gettext` / `gettext_lazy` and are translated in `locale/pt_BR`;
  - docs are mirrored in `docs/pt-BR/`.
- Never hard-code a user-facing string without wrapping it for translation.

## Code standards

### Python
- **PEP 8**, enforced by `ruff check` + `ruff format` with line length 88.
- **PEP 257** docstrings on every module, public class and public function.
- Type hints on all function signatures.
- **About 150 LOC per file. Over 300 is a hard limit and CI fails.**
  - Split by responsibility before a file grows past that.
- Business logic lives in `services/`. Views, serializers and admin stay thin.
- Never duplicate a rule across validators, serializers and services: reuse one source.
- Use `__init__.py` re-exports for centralized imports, e.g. `models/__init__.py`.
- Chunk complex flows (signup, login + 2FA, AI execution) into focused modules.
  - Use one orchestrator, plus steps, plus helpers.

### Django app layout
Every SDK app follows this layout. Each file stays at about 150 LOC; split into a subpackage if it grows.

```
tripaulx/<app>/
├── __init__.py
├── apps.py              # AppConfig with label = "tpsdk_<app>"
├── conf.py              # app defaults read from settings.TRIPAULX
├── models/              # one file per model + __init__ re-exports
├── api/
│   ├── serializers/     # grouped by model domain
│   ├── views/           # one file per resource or flow
│   ├── permissions.py
│   └── urls.py
├── services/            # business logic and side effects
├── validators/
├── tasks/               # django.tasks background jobs
├── admin/
├── management/commands/
├── locale/pt_BR/LC_MESSAGES/
├── migrations/
└── tests/               # pytest + factory_boy, <150 LOC per test file
```

- `models/base.py` is not repeated in each app. Every model inherits `tripaulx.core.models.BaseModel` (UUID pk, audit, soft delete) unless there is a stated reason not to.
- App labels are always `tpsdk_<app>` so they never collide with project apps (e.g. `core`, `accounts`, or apps already prefixed `tripaulx_`).

### Settings
- Settings are split into chunks: `config/settings/base.py` only imports from `base_parts/`.
- Environments are `local.py`, `prod.py` and `test.py`. `tripaulx.settings.env.load_environment` reads `.env.<env>`.
- SDK options live in one `TRIPAULX = {...}` dict.
  - Each SDK app declares its defaults in `conf.py` as `app_settings = AppSettings({...})`, using `tripaulx.core.conf`.
  - Code reads options only through that `app_settings`.

### Tests
- Use pytest + pytest-django + factory_boy.
- Each test file covers one feature or scenario and stays under 150 LOC.
- Shared setup goes in `conftest.py` and factories.
- Tenant tests use `tripaulx.core.testing.TenantTestCase`.

### Migrations
- **Never** remove or rename a field without explicit confirmation from the user.
- Before running a migration, check that it does not drop anything.
- SDK migrations must stay backwards compatible within a minor version (semver).

### Tooling
- Always use `uv run ...`, e.g. `uv run python manage.py ...` and `uv run pytest`.
- Always set `DJANGO_SETTINGS_MODULE` explicitly: `config.settings.local`, `.prod` or `.test`.
- Multi-tenant migrations use `migrate_schemas`, never plain `migrate`.

## Repository commands
- `uv sync`: install the workspace (root + sdk).
- `cd sdk && uv run pytest`: SDK tests against local PostgreSQL.
- `scripts/render_example.sh`: render `template/` into the gitignored `example/`. Then run `cd example && ./start setup && ./start test`.
- `uv run python scripts/check_file_size.py`: check file sizes.
- `scripts/check_translations.sh`: check that every string has a pt-BR translation.
- `uv run --group docs python -m scripts.readme_art`: regenerate the README diagrams in `docs/assets/readme/`.
  - Copy lives in `scripts/readme_art/copy/*.toml` (en + pt). Drawings live in `scripts/readme_art/diagrams/`.
  - Never edit the generated SVGs by hand.
- When a template file changes, re-render, run `ruff check --fix` and `ruff format` in `example/`, and copy any fixes back into `template/`.

## Claude Code plugin
- `.claude-plugin/marketplace.json` (marketplace `tripaulx`) lists the plugin in `plugin/`, named `tripaulx-builder`.
- Its skills are `plugin/skills/new-project` and `plugin/skills/update-project`.
- After any change to them, run `claude plugin validate . --strict && claude plugin validate ./plugin --strict`.
- Keep the skills in sync with the Copier questions (`copier.yml`) and with `./start`.

## Public repository hygiene
- This repository is public. Never write any of the following into it:
  - internal project names, client or tenant names, or people's names (the only exception is the maintainer, Flavio Almeida Paulino <f1@tripaulx.com>);
  - private domains, IPs, server names, app names or local absolute paths.
- This covers code, comments, docstrings, docs, test fixtures and commit messages.
- Use neutral examples instead: `example.com`, `acme`, "Acme Ltda".
- Never commit secrets, real customer data or personal data. CI runs gitleaks.
