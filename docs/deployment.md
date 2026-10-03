# Deployment

> Portuguese: [pt-BR/deployment.md](pt-BR/deployment.md)

Projects generated from `template/` deploy to [CapRover](https://caprover.com).
The full step-by-step guide ships with every project, rendered with its own
answers: [`template/docs/deployment.md.jinja`](../template/docs/deployment.md.jinja)
(pt-BR: [`template/docs/pt-BR/deployment.md.jinja`](../template/docs/pt-BR/deployment.md.jinja)).

## Summary

- **One image, two roles.** `template/Dockerfile` builds a single
  `python:3.13-slim` image (uv, `uv sync --frozen --no-dev`, non-root user,
  `collectstatic` at build, `HEALTHCHECK`). `APP_ROLE=web` runs gunicorn;
  `APP_ROLE=worker` runs `manage.py db_worker` for `django.tasks`.
- **Four CapRover apps per project:** `<slug>` (web), `<slug>-worker`,
  PostgreSQL and Redis (one-click apps).
- **Boot:** `entrypoint.sh` checks the required variables, waits for the
  database, then runs `migrate_schemas --shared`, `bootstrap_workspace` and
  `migrate_schemas` (web only by default, `RUN_MIGRATIONS`).
- **Deploy:** `./deploy prod [web|worker|all]` runs `scripts/check.sh`
  (ruff + pytest; skip with `SKIP_CHECKS=1`), then `scripts/caprover-deploy.sh`
  packs the project and uploads it with per-app tokens from `.env.deploy`.
- **Variables:** `.env.prod.example` lists every runtime variable the code
  reads; `.env.deploy.example` lists the deploy-only ones.
- **Wildcard subdomains** (`<slug>.<APP_BASE_DOMAIN>`), configured once:
  - a Cloudflare proxied `A *` record with SSL in Full (strict);
  - a Cloudflare Origin CA certificate for `*.domain` + apex on the CapRover host;
  - a guarded `server_name *.domain` block in the web app's nginx template.
- **Boundaries:** the code never calls the CapRover API, and the CapRover
  password never goes into any app's environment.

## CI

The `deploy` job in `.github/workflows/ci.yml` renders the template, vendors
the local SDK into the example (the SDK is not on PyPI yet), runs
`docker build` and `shellcheck` on every shell script of the template.
