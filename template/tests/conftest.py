"""Project-wide pytest fixtures."""

from collections.abc import Iterator

from django.conf import settings
from django.test import override_settings
import pytest


@pytest.fixture(autouse=True)
def _object_storage_offline() -> Iterator[None]:
    """Never reach a bucket and store files in clear, whatever .env.* holds.

    ``./start`` writes APP_FILE_ENCRYPTION_KEY into .env.local, and settings
    are imported before this conftest runs, so the key is blanked per test.
    Tests that want encryption enter their own override, which wins.
    """
    offline = {"S3_ENABLED": False, "FILE_ENCRYPTION_KEY": ""}
    with override_settings(TRIPAULX={**settings.TRIPAULX, **offline}):
        yield
