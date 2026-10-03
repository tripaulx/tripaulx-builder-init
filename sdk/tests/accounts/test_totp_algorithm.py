"""The hand-written TOTP matches the RFC 6238 test vectors."""

import base64

import pytest

from tripaulx.accounts.services import totp

#: Secret of the RFC 6238 SHA1 vectors, in base32.
RFC_SECRET = base64.b32encode(b"12345678901234567890").decode()


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        (59, "94287082"),
        (1111111109, "07081804"),
        (1111111111, "14050471"),
        (1234567890, "89005924"),
        (2000000000, "69279037"),
        (20000000000, "65353130"),
    ],
)
def test_rfc_6238_vectors(timestamp, expected):
    assert totp.code_at(RFC_SECRET, timestamp, digits=8) == expected


def test_rfc_4226_hotp_vectors():
    expected = ["755224", "287082", "359152", "969429", "338314"]
    assert [totp.hotp(RFC_SECRET, counter) for counter in range(5)] == expected


def test_window_accepts_neighbour_steps_only():
    now = 1_700_000_000
    secret = totp.generate_secret()
    previous = totp.code_at(secret, now - 30)
    following = totp.code_at(secret, now + 30)
    far = totp.code_at(secret, now + 90)
    assert totp.matching_step(secret, previous, timestamp=now) is not None
    assert totp.matching_step(secret, following, timestamp=now) is not None
    assert totp.matching_step(secret, far, timestamp=now) is None
    assert totp.matching_step(secret, "12345", timestamp=now) is None


def test_secret_is_32_base32_characters():
    assert len(totp.generate_secret()) == 32
    assert set(totp.generate_secret()) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")


def test_provisioning_uri():
    uri = totp.provisioning_uri("ABC234", "jane@example.com", "Acme")
    assert uri.startswith("otpauth://totp/Acme:jane@example.com?")
    assert "secret=ABC234" in uri
    assert "issuer=Acme" in uri
    assert "digits=6" in uri


def test_qr_svg_has_no_fixed_size():
    svg = totp.qr_svg("otpauth://totp/Acme:x@example.com?secret=ABC")
    assert svg.startswith("<svg") or svg.startswith("<?xml")
    assert 'width="' not in svg[:200]
