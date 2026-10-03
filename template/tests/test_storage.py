from django.conf import settings
from tripaulx.storage.conf import app_settings


def test_storage_app_is_installed():
    assert "tripaulx.storage" in settings.INSTALLED_APPS


def test_tests_never_reach_a_bucket_and_store_in_clear():
    assert app_settings.S3_ENABLED is False
    assert app_settings.FILE_ENCRYPTION_KEY == ""
