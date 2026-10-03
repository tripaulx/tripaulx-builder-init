"""Errors raised by the storage app."""

from django.core.exceptions import ImproperlyConfigured


class StorageError(Exception):
    """A storage operation failed; the message is safe to show to the caller."""


def missing_dependency(package: str) -> ImproperlyConfigured:
    """Return the error raised when an optional dependency is not installed."""
    return ImproperlyConfigured(
        f"tripaulx.storage needs '{package}'. Install the optional "
        'dependencies with: pip install "tripaulx-sdk[storage]"'
    )
