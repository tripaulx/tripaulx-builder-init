# Changelog

All notable changes to **tripaulx-sdk** and the project template are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-11-16

Everything here is additive: with the default settings a project behaves as
it did on 0.2.

### Changed (dependencies)
- Minimum versions raised to the current releases, so a new install can no longer resolve an older, unpatched one:
  - Django `>=6.0.10` on the 6.0 series and `>=6.1.3` on 6.1 (6.1.0 to 6.1.2 are excluded);
  - django-tenants `>=4.0.4,<5` (it was `<4`);
  - djangorestframework `>=3.18.3`, simplejwt `>=5.5.1`, drf-spectacular `>=0.30`, psycopg `>=3.3.9`, cryptography `>=50.0.2`, nh3 `>=0.3.7`, python-dotenv `>=1.2.4`, qrcode `>=8.2`, webauthn `>=3.0.1`;
  - extras: boto3 `>=1.44`, pillow `>=13`, openai `>=3.52`, anthropic `>=2.9`.
- Template: Django `>=6.1.3`, gunicorn `>=27.0.1`.

### Added
- **Account registration inside a workspace.** `POST /api/auth/register/` creates a member without an invitation, for consumer products. Off by default (`REGISTRATION_ENABLED`).
  - `REGISTRATION_PROFILES` declares the kinds of account and the user-model fields each one requires or accepts; `REGISTRATION_FIELDS` and `REGISTRATION_PROFILE_FIELD` complete it.
  - Extra fields are validated by the project's own `User` model fields. Access fields (`role`, `is_staff`...) can never be written.
  - New signal `user_registered` (`user`, `profile`, `extra`).
- **`MFA_POLICY`**: `always` (default), `privileged` (staff, owners and admins) or `optional`. A user with an authenticator app is always asked.
- **`EMAIL_VERIFICATION_REQUIRED`** (default `True`). Off, signup and registration create verified accounts and answer with a `session`.
- Signup answers with `workspace_name`, `api_url` and `session` too.
- `GET /api/auth/config/` (anonymous): the flags a client needs before rendering its auth screens.
- `GET /api/auth/workspaces/<slug>/` (public schema): whether a workspace exists or the address is free. New throttle scope `auth_lookup`.
- `tripaulx.tenants.services.domains`: `workspace_origin`, `workspace_origin_template` and `request_origin`.
- `tripaulx.tenants.services.schemas.workspace_schemas` (it lived in `tripaulx.ai.services.retention`, where it stays importable).
- `tripaulx.mail`:
  - `email_available()` tells whether sent e-mail reaches anyone;
  - `send_test_mail` management command;
  - a DEBUG-only preview (`tripaulx.mail.urls`) and `register_sample` for the project's own e-mails.
- Template:
  - `APP_EMAIL_VERIFICATION_REQUIRED`, `APP_MFA_POLICY` and `APP_REGISTRATION_ENABLED`;
  - the e-mail preview route;
  - production no longer points at SMTP on `localhost` when `MAIL_HOST` is empty: messages are dropped until a provider is configured.

## [0.2.2] - 2026-10-07

### Added
- `POST /api/workspace/members/<id>/reactivate/` (owners and admins) gives a deactivated member access again, with the same role. Owner rules apply: only an owner reactivates an owner. Service: `tripaulx.accounts.services.members.reactivate`.

## [0.2.1] - 2026-10-06

### Fixed
- The public schema's Django admin no longer fails with `relation "tpsdk_ai_aisettings" does not exist`. The AI admins (settings, agents, skills, keys, events) are now hidden outside workspace schemas, where their tables live, and answer their permission checks there without querying the database.

### Added
- `tripaulx.core.admin_scope`: `PublicSchemaAdmin` and `WorkspaceSchemaAdmin` ModelAdmin mixins that keep a model to the schemas where its table exists.

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

[Unreleased]: https://github.com/tripaulx/tripaulx-builder-init/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/tripaulx/tripaulx-builder-init/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/tripaulx/tripaulx-builder-init/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/tripaulx/tripaulx-builder-init/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tripaulx/tripaulx-builder-init/releases/tag/v0.1.0
