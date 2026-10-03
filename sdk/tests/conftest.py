"""Shared pytest fixtures for the SDK test-suite."""

from __future__ import annotations

from collections.abc import Iterator

from django.core import mail
from django.core.cache import cache
from django.db import connection
import pytest


@pytest.fixture(autouse=True)
def _fresh_cache_and_outbox() -> Iterator[None]:
    """Reset throttle counters, WebAuthn challenges and sent e-mails."""
    cache.clear()
    mail.outbox = []
    yield
    cache.clear()


@pytest.fixture
def public_schema() -> Iterator[None]:
    """Run the test on the public schema and restore it afterwards."""
    connection.set_schema_to_public()
    yield
    connection.set_schema_to_public()
