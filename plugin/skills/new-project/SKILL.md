---
name: new-project
description: Create a new tripaulx-builders project (multi-tenant Django 6.1 + django-tenants on tripaulx-sdk, with workspaces per subdomain, mandatory 2FA, passkeys, AI providers, encrypted storage, legal documents and CapRover deploy) from the tripaulx-builder-init Copier template, then set it up and verify it runs. Use when the user wants to start, scaffold, bootstrap or initialize a new tripaulx project, a new SaaS backend on tripaulx-sdk, or "a new project like the tripaulx base".
argument-hint: "[project-name] [target-directory]"
allowed-tools: Bash(uv --version) Bash(uvx copier *) Bash(pg_isready *) Bash(git init*) Bash(git add *) Bash(git commit *) Bash(./start setup) Bash(./start test*) Bash(./pg *)
---

# Create a tripaulx-builders project

The project is generated from the public template
`gh:tripaulx/tripaulx-builder-init` and depends on
[`tripaulx-sdk`](https://pypi.org/project/tripaulx-sdk/) from PyPI. It is backend
only: a DRF API and the Django admin.

Arguments: `$ARGUMENTS`. They are an optional project name, then an optional target
directory. The directory defaults to the slug of the name, inside the current
working directory.

## 1. Check prerequisites

Run these checks and stop with a clear explanation if one fails:
- `uv --version` must work. If it does not, tell the user to install uv
  (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- `pg_isready -h 127.0.0.1` must print "accepting connections".
  - PostgreSQL 16+ is required, because django-tenants needs schemas; SQLite does not work.
  - On macOS with Homebrew, `brew services start postgresql@16` starts it.
  - The project's `./pg ensure` creates the role and the database, connecting as the OS user.
- The target directory must not exist, or must be empty. Never overwrite files.

## 2. Collect the answers

Ask only for what the user has not given already. Offer the defaults and accept them
when the user says so.

| Copier key | Ask | Default |
|---|---|---|
| `project_name` | Project name | from `$ARGUMENTS` |
| `project_slug` | Python/database identifier | name lowercased, spaces/dashes → `_` |
| `base_domain` | Production apex domain; workspaces are served at `<slug>.<domain>` | `example.com` |
| `initial_workspace` | Slug of the first workspace | `main` |
| `language_code` | Default language, `pt-br` or `en` | `pt-br` |
| `time_zone` | Time zone | `America/Sao_Paulo` |
| `default_from_email` | Sender address | `noreply@<base_domain>` |

The slug must match `^[a-z][a-z0-9_]{1,40}$`. The first workspace slug must be 3-30
lowercase letters, digits or `_`, start with a letter, and avoid reserved names (`www`,
`api`, `app`, `admin`, `mail`, `static`, `demo`, `test`...).

## 3. Generate

```bash
uvx copier copy --trust --defaults \
  --data project_name="<name>" --data project_slug="<slug>" \
  --data base_domain="<domain>" --data initial_workspace="<workspace>" \
  --data language_code="<lang>" --data time_zone="<tz>" \
  --data default_from_email="<email>" \
  gh:tripaulx/tripaulx-builder-init <directory>
```

`--trust` is required because the template ships executable scripts.
`.copier-answers.yml` records the answers; `copier update` needs that file later.

## 4. Set up and verify

Run these from the new directory:
1. `./start setup` creates `.env.local` with fresh keys (`SECRET_KEY`, `APP_FIELD_ENCRYPTION_KEY`, `APP_FILE_ENCRYPTION_KEY`) and the database. It then migrates the public schema, creates the public and first-workspace domains, and migrates every workspace.
2. `./start test` runs the test-suite; it must pass.

Claude's shell is not a terminal, so `./start setup` skips the owner prompt and
prints `no terminal: ... run ./start admin`. Step 5 creates the owner instead.

If a step fails, read the output and fix the cause. Do not skip the step. Common
causes:
- PostgreSQL is not running;
- the `DB_USER` role exists with another password;
- a stale `.env.local`.

## 5. The first workspace's owner (onboarding)

Every workspace needs an owner to sign in. Ask the user for:
- **full name**;
- **e-mail**, which is the login (there is no separate username).

Then show the password rules. They are the project's `AUTH_PASSWORD_VALIDATORS`, so
read them with:

```bash
uv run python manage.py shell -c "from tripaulx.accounts.services.identity import password_rules; print(*password_rules(), sep='\n')"
```

By default: at least 8 characters, not too similar to the name or e-mail, not a
common password, not entirely numeric.

Prefer that **the user types the password in their own terminal**, so it never goes
through the conversation:

```bash
./start admin --email "<email>" --full-name "<full name>"
```

It asks for the password twice, hidden, re-asks when a rule fails, and creates the
owner with a verified e-mail and Django admin access. In Claude Code the user can run
it with `!` only if their shell is interactive; otherwise they use a normal terminal.

Only if the user explicitly wants to type the password in the chat:
- ask for the password and its confirmation;
- compare them;
- pipe the password through stdin, never on the command line, and never write it to a file or repeat it back:

```bash
printf '%s\n' '<password>' | ./start admin --email "<email>" --full-name "<full name>" --password-stdin
```

If the command reports a rule violation, relay the message and ask again.

## 6. Version control

Ask before running git. If the user agrees:

```bash
git init -b main && git add -A && git commit -m "chore: start project from tripaulx-builder-init"
```

`.env.local` is already gitignored. Never commit it.

## 7. Hand over

Tell the user, briefly:
- **Run it:** `./start` serves on :8000, at:
  - public: `http://<slug-with-dashes>.localhost:8000/admin/`;
  - first workspace: `http://<workspace>.<slug-with-dashes>.localhost:8000/admin/`.
- **More administrators:** `./start admin`, with `--role admin|member` and `--no-superuser` available.
- **API:** auth at `/api/auth/` (sign-up only on the public domain), members at `/api/workspace/`, AI at `/api/v1/ai/`, legal at `/api/v1/legal/` and `/api/legal/public/`.
- **Conventions:** the generated `CLAUDE.md` holds the code standards; follow it when writing the business apps:
  - English code with pt-BR translations;
  - files of about 150 lines (300 at most);
  - business logic in `services/`;
  - new apps in `PROJECT_TENANT_APPS`.
- **Deploy:** read `docs/deployment.md` (CapRover, wildcard subdomains). Production needs `APP_FIELD_ENCRYPTION_KEY` and `SECRET_KEY`.
- **Updates later:** use the `update-project` skill of this plugin.

See [reference.md](reference.md) for the generated layout and the environment
variables.
