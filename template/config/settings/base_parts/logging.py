"""Logging with secret redaction on the console handler."""

from tripaulx.settings.observability import logging_config

from .common import get_env

LOGGING = logging_config(get_env("LOG_LEVEL", "INFO"))
