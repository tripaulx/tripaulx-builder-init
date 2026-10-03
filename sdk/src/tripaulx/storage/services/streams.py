"""File-like adapters between boto3 and the chunked encryption."""

from __future__ import annotations

from typing import Any, BinaryIO

from .. import crypto


class EncryptingStream:
    """Adapt :func:`crypto.encrypt_stream` to the ``read(n)`` boto3 expects.

    boto3 pulls the body in pieces; ciphertext is produced on demand and only
    the remainder of one piece is held between reads, so a large file never
    sits whole in memory, neither in clear nor encrypted.
    """

    def __init__(self, source: BinaryIO) -> None:
        """Start encrypting ``source`` lazily."""
        self._pieces = crypto.encrypt_stream(source)
        self._buffer = b""
        self._done = False

    def read(self, size: int | None = -1) -> bytes:
        """Return up to ``size`` bytes of ciphertext (all of it when negative)."""
        if size is None or size < 0:
            parts = [self._buffer, *self._pieces]
            self._buffer, self._done = b"", True
            return b"".join(parts)

        while len(self._buffer) < size and not self._done:
            try:
                self._buffer += next(self._pieces)
            except StopIteration:
                self._done = True

        out, self._buffer = self._buffer[:size], self._buffer[size:]
        return out


class PeekedStream:
    """File-like that returns already-read bytes before the rest of the source.

    Telling whether an object is encrypted means reading its first bytes; the
    decryption then needs the WHOLE object from byte zero. This puts the peeked
    bytes back in front (an S3 ``Body`` cannot seek backwards).
    """

    def __init__(self, peeked: bytes, rest: Any) -> None:
        """Serve ``peeked`` first, then read from ``rest``."""
        self._peeked = peeked
        self._rest = rest

    def read(self, size: int | None = -1) -> bytes:
        """Return up to ``size`` bytes (everything when negative)."""
        if size is None or size < 0:
            out, self._peeked = self._peeked, b""
            return out + self._rest.read()
        if not self._peeked:
            return self._rest.read(size)
        out, self._peeked = self._peeked[:size], self._peeked[size:]
        if len(out) < size:
            out += self._rest.read(size - len(out))
        return out
