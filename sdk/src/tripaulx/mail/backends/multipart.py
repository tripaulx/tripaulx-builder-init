"""Minimal ``multipart/form-data`` encoder (stdlib only, text fields)."""

from __future__ import annotations

import uuid


def encode_multipart(fields: list[tuple[str, str]]) -> tuple[bytes, str]:
    """Encode ``(name, value)`` pairs; return ``(body, content_type)``.

    Repeated names are allowed (e.g. one ``to`` field per recipient).
    """
    boundary = uuid.uuid4().hex
    lines: list[str] = []
    for name, value in fields:
        lines += [
            f"--{boundary}",
            f'Content-Disposition: form-data; name="{name}"',
            "",
            value,
        ]
    lines += [f"--{boundary}--", ""]
    body = "\r\n".join(lines).encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"
