"""Logging filter that masks secrets and personal data before output.

Production logs go to the CapRover console with no retention control. This
filter rewrites every formatted message, replacing e-mails, bearer tokens,
JWTs, API keys (``sk-``), authorization headers and one-time codes that appear
next to an OTP keyword. It is a safety net, not a licence to log content.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
import re

MASK = "[redacted]"

Replacement = str | Callable[[re.Match[str]], str]


def _header(match: re.Match[str]) -> str:
    """Keep the header name and scheme, mask the credential."""
    scheme = f"{match.group(3)} " if match.group(3) else ""
    return f"{match.group(1)}{match.group(2)}{scheme}{MASK}"


PATTERNS: list[tuple[re.Pattern[str], Replacement]] = [
    (
        re.compile(
            r"(?i)(authorization|http_authorization)"
            r"(\s*[:=]\s*)(?:(bearer|token|basic)\s+)?\S+"
        ),
        _header,
    ),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"), f"Bearer {MASK}"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), MASK),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"), f"sk-{MASK}"),
    # E-mails keep only the domain, which is still useful for investigation.
    (re.compile(r"\b[\w.+-]+@([\w-]+\.)+[\w-]{2,}\b"), f"{MASK}@..."),
    (
        re.compile(r"(?i)\b(c[oó]digo|code|otp|token)(\s*[:=]?\s*)\d{6}\b"),
        rf"\1\2{MASK}",
    ),
]


def redact(text: str) -> str:
    """Apply every mask to ``text`` and return the result."""
    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactSecretsFilter(logging.Filter):
    """Rewrite ``record.msg`` with secrets masked; never drops a record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact the formatted message in place."""
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - malformed args: leave untouched
            return True
        redacted = redact(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True
