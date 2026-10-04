# Changelog

All notable changes to **tripaulx-sdk** and the project template are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-10-04

### Changed (breaking API)
- Signup requires `full_name` and `password_confirm`. The full name fills `first_name`/`last_name`.
- Password reset confirm, password change and invitation acceptance require the confirmation: `password_confirm` / `new_password_confirm`.
- Passwords are validated against the person (e-mail, first and last name) everywhere, including signup, so `UserAttributeSimilarityValidator` applies before the user exists. Errors carry `field: "password"` or `field: "password_confirm"`.

### Added
- `GET /api/auth/password/rules/` (anonymous) returns the active password rules, translated.
- `create_workspace_admin` management command:
  - asks for full name, e-mail and the password twice, shows the rules and repeats on failure;
  - creates a verified owner with Django admin access;
  - options `--role`, `--no-superuser`, `--password-stdin` and `--if-none`.
- Template:
  - `./start setup` asks for the first workspace's owner when run in a terminal (onboarding);
  - `./start admin` creates more administrators.
- The `new-project` skill collects the owner's full name and e-mail and creates the owner. It prefers the user typing the password in their own terminal.
- Claude Code plugin marketplace (`tripaulx`) with the `tripaulx-builder` plugin:
  - the `new-project` skill creates, sets up and verifies a project from the template;
  - the `update-project` skill applies template and SDK updates.

## [0.1.0] - 2026-10-03

First release.

### Core and settings
- `tripaulx.core`:
  - `BaseModel` (UUID primary key, audit timestamps, soft delete) with `AliveManager`;
  - `TenantMiddleware`, which answers `/healthz` and `/readyz` before tenant lookup and skips static files;
  - log redaction of e-mails, tokens, keys and one-time codes;
  - `AppSettings`, which reads the single `TRIPAULX` options dict;
  - test helpers `TenantTestCase` and `TenantAPITestCase`.
- `tripaulx.core.crypto`: Fernet field encryption with `FIELD_ENCRYPTION_KEY`. Production refuses to start without a valid key.
- `tripaulx.settings`: helpers for `.env` loading, app lists, middleware, logging and hosts. The `rest` module adds `rest_framework()`, `simple_jwt()` and `spectacular()`.

### Workspaces
- `tripaulx.tenants`:
  - `Workspace` and `Domain`, one PostgreSQL schema per workspace, served at `<slug>.<base domain>`;
  - slug rules with reserved names;
  - `bootstrap_workspace`, idempotent;
  - `provision_workspace` and the `workspace_created` signal.

### Accounts
- `tripaulx.accounts`:
  - e-mail login with mandatory 2-step verification: authenticator app (TOTP), or a 6-digit e-mail code;
  - recovery codes and trusted devices;
  - passkeys (WebAuthn) with a passkey-only mode;
  - password reset and change, both of which end every session;
  - JWTs bound to the workspace schema.
- Public sign-up (`POST /api/auth/signup/`) creates the workspace, its schema, its domain and the owner.
- Workspace members and invitations (`/api/workspace/`): owner, admin and member roles; the last owner is always kept.
- `tripaulx.mail`: Mailgun backend with an encrypted key and a fallback backend, configured through Django 6.1 `MAILERS`, with branded e-mail templates projects can override.

### Storage
- `tripaulx.storage` (extra `tripaulx-sdk[storage]`):
  - S3-compatible storage with keys scoped to each workspace;
  - client-side envelope encryption: AES-256-GCM, 1 MiB authenticated chunks, a key per file;
  - a configurable upload policy: MIME allowlist with magic-byte checks, size limits, image pixel limit;
  - the `generate_file_key` and `check_bucket` commands.

### AI
- `tripaulx.ai` (extras `tripaulx-sdk[openai]`, `[anthropic]`, `[ai]`):
  - OpenAI (Responses API) and Anthropic (Messages API) behind a pluggable provider registry;
  - per-workspace settings with a daily cost cap;
  - one encrypted key per provider, with history;
  - agents (specialist, or coordinator with a team), versioned skills, and usage events with cost, tokens, latency and errors;
  - reports and a dashboard;
  - background runs through `django.tasks`.
- Shared model catalog in the public schema (`tripaulx.ai.catalog`), seeded with current OpenAI and Anthropic models and prices, plus `ai_sync_catalog`.
- API `/api/v1/ai/`: settings, keys and agent/skill writes are owner/admin only, event content is admin only, and runs are throttled.
- Content retention with `ai_purge_content` and the `purge_ai_content` task.

### Legal
- `tripaulx.legal`:
  - generic English and pt-BR documents: terms of use, privacy policy (LGPD and GDPR), risk matrix, incident response plan, incident register, incident record template, data inventory, governance backlog;
  - placeholders filled from `LEGAL_CONTEXT`, and project overrides from `LEGAL_CONTENT_DIRS`;
  - Markdown rendered to sanitized HTML;
  - restricted and public APIs, and `legal_check`.

### Project template (Copier)
- Settings split into chunks.
- `users` app.
- `./start` and `./pg`; `./start` generates the local keys.
- Smoke tests.
- CapRover deploy:
  - one `python:3.13-slim` image running as web (gunicorn) or worker (`db_worker`), non-root, with `collectstatic` at build and a healthcheck;
  - `./deploy prod [web|worker|all]`;
  - `.env.prod.example` and `.env.deploy.example`.
- Guides (en and pt-BR) for deployment with wildcard subdomains (Cloudflare + Origin CA + nginx), accounts, storage, AI and legal.
- pt-BR translations for every user-facing string.

### Repository
- CI:
  - lint, file size and translation checks;
  - SDK matrix (Python 3.12/3.13 × Django 6.0/6.1 × PostgreSQL 16/17);
  - end-to-end template render with OpenAPI validation and `check --deploy`;
  - Docker build and boot test;
  - shellcheck;
  - gitleaks.
- Release workflow with PyPI Trusted Publishing.
- README (en and pt-BR) with diagrams in the tripaulx design system.

[Unreleased]: https://github.com/tripaulx/tripaulx-builder-init/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/tripaulx/tripaulx-builder-init/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tripaulx/tripaulx-builder-init/releases/tag/v0.1.0
