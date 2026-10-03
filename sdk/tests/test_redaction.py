import logging

import pytest

from tripaulx.core.logs.redaction import MASK, RedactSecretsFilter, redact


@pytest.mark.parametrize(
    ("raw", "leaked"),
    [
        ("Authorization: Bearer abc.def.ghi", "abc.def.ghi"),
        ("token eyJhbGciOi.eyJzdWIiOi.c2lnbmF0dXJl here", "eyJhbGciOi"),
        ("key sk-proj_ABCDEFGH1234 used", "ABCDEFGH1234"),
        ("sent to jane.doe@example.com", "jane.doe"),
        ("verification code: 123456", "123456"),
    ],
)
def test_secrets_are_masked(raw, leaked):
    redacted = redact(raw)
    assert leaked not in redacted
    assert MASK in redacted


def test_plain_numbers_survive():
    assert redact("processed 123456 rows") == "processed 123456 rows"


def test_filter_rewrites_record_with_args():
    record = logging.LogRecord(
        "x", logging.INFO, __file__, 1, "user %s logged in", ("a@b.com",), None
    )
    assert RedactSecretsFilter().filter(record) is True
    assert record.getMessage() == f"user {MASK}@... logged in"
