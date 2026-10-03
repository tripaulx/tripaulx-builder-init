import logging

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
import pytest

from tripaulx.core import crypto

KEY = Fernet.generate_key().decode()


def test_round_trip_and_empty_values():
    token = crypto.encrypt("s3cret")
    assert token and token != "s3cret"
    assert crypto.decrypt(token) == "s3cret"
    assert crypto.encrypt("") == ""
    assert crypto.decrypt("") == ""


def test_configured_key_is_used():
    with override_settings(TRIPAULX={"FIELD_ENCRYPTION_KEY": KEY}):
        token = crypto.encrypt("plain-secret")
    assert Fernet(KEY.encode()).decrypt(token.encode()) == b"plain-secret"


def test_fallback_key_derives_from_secret_key():
    token = crypto.encrypt("plain-secret")
    with override_settings(SECRET_KEY="another-secret"):
        assert crypto.decrypt(token) == ""


def test_wrong_key_logs_and_returns_empty(caplog):
    with override_settings(TRIPAULX={"FIELD_ENCRYPTION_KEY": KEY}):
        token = crypto.encrypt("plain-secret")
    other = Fernet.generate_key().decode()
    with override_settings(TRIPAULX={"FIELD_ENCRYPTION_KEY": other}):
        with caplog.at_level(logging.ERROR, logger="tripaulx.crypto"):
            assert crypto.decrypt(token) == ""
    assert "FIELD_ENCRYPTION_KEY" in caplog.text
    assert "plain-secret" not in caplog.text


def test_garbage_token_returns_empty():
    assert crypto.decrypt("not-a-token") == ""


def test_validate_field_key():
    crypto.validate_field_key(KEY)
    crypto.validate_field_key(crypto.generate_key())
    for bad in ("", None, "short", "x" * 44):
        with pytest.raises(ImproperlyConfigured):
            crypto.validate_field_key(bad)
