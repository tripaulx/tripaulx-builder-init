"""TOTP (RFC 6238) without third-party code, plus the provisioning QR code.

The algorithm is short and fully specified: HMAC-SHA1 of the 30-second
counter, dynamic truncation, 6 digits. It is checked against the RFC test
vectors in the test-suite. Only the QR encoder comes from a library
(``qrcode``, pure Python).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import struct
import time
from urllib.parse import quote

DIGITS = 6
PERIOD = 30
#: Steps of tolerance on each side of "now" (phone clocks drift).
WINDOW = 1
#: 20 bytes = 160 bits, the full key size HMAC-SHA1 uses.
SECRET_BYTES = 20


def generate_secret() -> str:
    """Return a new base32 secret (32 characters, no padding)."""
    return base64.b32encode(secrets.token_bytes(SECRET_BYTES)).decode().rstrip("=")


def hotp(secret_b32: str, counter: int, digits: int = DIGITS) -> str:
    """HOTP (RFC 4226): HMAC-SHA1 of the counter, dynamic truncation."""
    padded = secret_b32.upper() + "=" * (-len(secret_b32) % 8)
    key = base64.b32decode(padded, casefold=True)
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = mac[-1] & 15
    number = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % (10**digits)).zfill(digits)


def step_at(timestamp: float | None = None, period: int = PERIOD) -> int:
    """Return the counter (step) ``timestamp`` falls in; ``None`` means now."""
    return int((time.time() if timestamp is None else timestamp) // period)


def code_at(
    secret_b32: str,
    timestamp: float | None = None,
    *,
    digits: int = DIGITS,
    period: int = PERIOD,
) -> str:
    """Return the TOTP code of ``secret_b32`` at ``timestamp`` (now if None)."""
    return hotp(secret_b32, step_at(timestamp, period), digits)


def matching_step(
    secret_b32: str, code: str, *, timestamp: float | None = None, window: int = WINDOW
) -> int | None:
    """Return the step ``code`` matches inside the window, or ``None``.

    Comparisons are constant-time and the whole window is always scanned, so
    the response time does not reveal where a match happened.
    """
    digits = re.sub(r"\D", "", code or "")
    if len(digits) != DIGITS:
        return None
    now = step_at(timestamp)
    found: int | None = None
    for delta in range(-window, window + 1):
        if hmac.compare_digest(hotp(secret_b32, now + delta), digits):
            found = now + delta
    return found


def provisioning_uri(secret_b32: str, email: str, issuer: str) -> str:
    """Return the ``otpauth://`` URI carried by the QR code."""
    label = quote(f"{issuer}:{email}", safe=":@")
    return (
        f"otpauth://totp/{label}?secret={secret_b32}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={DIGITS}&period={PERIOD}"
    )


def qr_svg(uri: str) -> str:
    """Return the QR code of ``uri`` as inline SVG without a fixed size."""
    import qrcode
    from qrcode.image.svg import SvgPathImage

    image = qrcode.make(uri, image_factory=SvgPathImage, box_size=10, border=2)
    svg = image.to_string(encoding="unicode")
    # Drop width/height so the client sizes it; the viewBox stays.
    return re.sub(r'\s(?:width|height)="[^"]*"', "", svg, count=2)
