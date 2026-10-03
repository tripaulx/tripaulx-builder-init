"""Loads the environment and re-exports the env helpers for other chunks."""

from pathlib import Path

from tripaulx.settings.env import (
    get_database_config,
    get_env,
    get_env_bool,
    get_env_int,
    get_env_list,
    load_environment,
)

# Project root (where manage.py, ./start and the .env files live).
BASE_DIR = Path(__file__).resolve().parents[3]

load_environment(BASE_DIR)

__all__ = [
    "BASE_DIR",
    "get_database_config",
    "get_env",
    "get_env_bool",
    "get_env_int",
    "get_env_list",
]
