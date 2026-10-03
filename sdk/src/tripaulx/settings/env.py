"""Environment loading and typed parsing for settings modules.

The ``.env`` file matching ``DJANGO_SETTINGS_MODULE`` is loaded without
overriding variables already present in the process (Docker, CI, shell), so
the real environment always wins over files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def env_file_for(settings_module: str) -> str:
    """Return the ``.env`` file name for a settings module path.

    ``config.settings.prod`` maps to ``.env.prod``, ``config.settings.local``
    to ``.env.local``; anything else falls back to ``.env``.
    """
    suffix = settings_module.rsplit(".", 1)[-1]
    if suffix in {"local", "prod", "test"}:
        return f".env.{suffix}"
    return ".env"


def load_environment(base_dir: Path, settings_module: str | None = None) -> None:
    """Load the environment-specific ``.env`` and then the generic ``.env``.

    Precedence (highest first): process environment, ``.env.<env>``, ``.env``.
    Every file is loaded with ``override=False``.
    """
    module = settings_module or os.environ.get(
        "DJANGO_SETTINGS_MODULE", "config.settings.local"
    )
    specific = env_file_for(module)
    for name in dict.fromkeys((specific, ".env")):
        path = base_dir / name
        if path.exists():
            load_dotenv(path, override=False)


def get_env(key: str, default: Any = None, required: bool = False) -> Any:
    """Return the variable ``key`` or ``default``.

    Raises:
        ValueError: when ``required`` is true and the value is missing/empty.
    """
    value = os.environ.get(key, default)
    if required and (value is None or value == ""):
        raise ValueError(
            f"Required environment variable is not set: {key}. "
            "Define it in the .env file or in the process environment."
        )
    return value


def get_env_bool(key: str, default: bool = False) -> bool:
    """Parse ``key`` as a boolean (``1``/``true``/``yes``/``on``)."""
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in _TRUE_VALUES


def get_env_int(key: str, default: int = 0) -> int:
    """Parse ``key`` as an integer, falling back to ``default`` when invalid."""
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_env_list(
    key: str, default: list[str] | None = None, sep: str = ","
) -> list[str]:
    """Parse ``key`` as a ``sep``-separated list of non-empty, stripped items."""
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return list(default or [])
    return [item.strip() for item in raw.split(sep) if item.strip()]


def get_database_config(prefix: str = "DB", default_name: str = "app") -> dict:
    """Build the default ``DATABASES`` entry from ``<prefix>_*`` variables.

    The engine defaults to the django-tenants PostgreSQL backend, which is
    required for schema-per-tenant isolation.
    """
    options: dict[str, Any] = {}
    sslmode = get_env(f"{prefix}_SSLMODE", "")
    if sslmode:
        options["sslmode"] = sslmode
    return {
        "ENGINE": get_env(f"{prefix}_ENGINE", "django_tenants.postgresql_backend"),
        "NAME": get_env(f"{prefix}_NAME", default_name),
        "USER": get_env(f"{prefix}_USER", default_name),
        "PASSWORD": get_env(f"{prefix}_PASSWORD", ""),
        "HOST": get_env(f"{prefix}_HOST", "127.0.0.1"),
        "PORT": get_env(f"{prefix}_PORT", "5432"),
        "CONN_MAX_AGE": get_env_int(f"{prefix}_CONN_MAX_AGE", 60),
        "OPTIONS": options,
    }
