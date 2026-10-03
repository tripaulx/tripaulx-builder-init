"""Shared pytest fixtures for the SDK test-suite."""

from __future__ import annotations

from collections.abc import Iterator

from django.db import connection
import pytest


@pytest.fixture
def public_schema() -> Iterator[None]:
    """Run the test on the public schema and restore it afterwards."""
    connection.set_schema_to_public()
    yield
    connection.set_schema_to_public()
