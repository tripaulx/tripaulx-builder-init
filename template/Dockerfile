# =============================================================================
# Production image for CapRover (Docker Swarm).
#
# One image serves two CapRover apps, chosen at runtime by APP_ROLE:
#   web     gunicorn on :8000 (default)
#   worker  `manage.py db_worker` (django.tasks queue in PostgreSQL)
#
# CapRover builds this image on the server from the tar sent by ./deploy.
# Secrets (SECRET_KEY, DB_*, ...) are never baked in: they are injected by
# CapRover at runtime (App Configs > Environment Variables).
# =============================================================================
FROM python:3.13-slim

# uv from its official image. Pin a tag (e.g. ghcr.io/astral-sh/uv:0.9) for
# fully reproducible builds; it must be at least the uv that wrote uv.lock.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod

ARG COMMIT_ID=unknown
ENV COMMIT_ID=${COMMIT_ID}

# curl is used by HEALTHCHECK (healthcheck.sh). Nothing else is needed: no
# Node, no system libraries for PDFs or images.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system app \
 && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

# Dependencies first (cached while pyproject.toml and uv.lock do not change).
# Local path dependencies, if any, are installed with the code below.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project --no-install-local

# Application code (.dockerignore keeps .git, .venv, .env* and caches out).
COPY . /app
RUN uv sync --frozen --no-dev

# collectstatic AT BUILD TIME, so a new container serves static files the
# moment it starts. The dummy values exist only in this RUN (not in the
# image): prod.py requires them at import time, but collectstatic never
# connects to the database nor decrypts anything. APP_FIELD_ENCRYPTION_KEY is
# a format-valid Fernet key made of zero bytes, never used at runtime.
RUN SECRET_KEY=build-only-not-used-at-runtime \
    APP_BASE_DOMAIN=build.invalid \
    APP_FIELD_ENCRYPTION_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
    DB_NAME=build DB_USER=build DB_PASSWORD=build DB_HOST=build DB_PORT=5432 \
    python manage.py collectstatic --noinput \
 && mkdir -p /app/media \
 && chown app:app /app/media \
 && chmod +x /app/entrypoint.sh /app/healthcheck.sh

USER app

EXPOSE 8000

# Per role (see healthcheck.sh): web asks /healthz/, worker checks that PID 1
# is db_worker. start-period covers migrations and boot.
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
  CMD ["/app/healthcheck.sh"]

ENTRYPOINT ["/app/entrypoint.sh"]
