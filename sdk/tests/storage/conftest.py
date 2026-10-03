"""Fixtures of the storage tests.

A test must not depend on the machine's environment: with a file key in a
local settings file, the "stored in clear" tests would start encrypting. The
key cannot be pinned through the environment (pytest-django imports settings
before conftest runs), hence an override around every test. Tests that WANT
encryption enter their own override afterwards, which wins.
"""

from collections.abc import Iterator

import pytest

from .helpers import override_tripaulx


@pytest.fixture(autouse=True)
def _file_encryption_off_by_default() -> Iterator[None]:
    """Default world of a test: files are stored in clear (no master key)."""
    with override_tripaulx(FILE_ENCRYPTION_KEY=""):
        yield
