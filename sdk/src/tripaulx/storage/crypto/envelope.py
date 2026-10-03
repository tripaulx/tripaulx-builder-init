"""The encrypted object format: one header, then authenticated chunks.

Layout::

    header = MAGIC | wrap nonce (12) | wrapped file key (32 + 16) | chunk (4)
    frame  = nonce (12) | flag (1) | ciphertext length (4) | ciphertext

The AAD of each chunk is ``header + index (4) + flag``; ``flag`` marks the last
chunk, so truncation is detected.
"""

from __future__ import annotations

from collections.abc import Iterator
import os
import struct
from typing import BinaryIO

from django.utils.translation import gettext as _

from ..exceptions import StorageError
from .keys import KEY_SIZE, aesgcm, master_key

#: Format marker and version. An object that does not start with it was not
#: encrypted by this module (for example a file stored in clear).
MAGIC = b"TPX1\x00"

#: Plaintext chunk size: 1 MiB keeps memory low and the 33-byte per-chunk
#: overhead negligible.
CHUNK = 1024 * 1024

_NONCE = 12  # AES-GCM
_TAG = 16
_HEADER_SIZE = len(MAGIC) + _NONCE + (KEY_SIZE + _TAG) + 4
_FRAME_SIZE = _NONCE + 1 + 4

_LAST = b"F"  # this chunk closes the file
_MIDDLE = b"C"


def is_encrypted(header: bytes) -> bool:
    """Return whether ``header`` starts with this module's format marker."""
    return header[: len(MAGIC)] == MAGIC


def encrypt_stream(source: BinaryIO) -> Iterator[bytes]:
    """Read the file-like ``source`` and yield the encrypted object in pieces.

    What comes out is what goes to the bucket, unreadable without the master
    key. Raises :class:`StorageError` for an empty source.
    """
    file_key = os.urandom(KEY_SIZE)
    wrap_nonce = os.urandom(_NONCE)
    wrapped = aesgcm(master_key()).encrypt(wrap_nonce, file_key, MAGIC)

    header = MAGIC + wrap_nonce + wrapped + struct.pack(">I", CHUNK)
    chunk = source.read(CHUNK)
    if not chunk:
        raise StorageError(_("The file is empty."))
    yield header

    cipher = aesgcm(file_key)
    index = 0
    while chunk:
        following = source.read(CHUNK)
        flag = _MIDDLE if following else _LAST
        nonce = os.urandom(_NONCE)
        body = cipher.encrypt(nonce, chunk, header + struct.pack(">I", index) + flag)
        yield nonce + flag + struct.pack(">I", len(body)) + body
        index += 1
        chunk = following


def decrypt_stream(source: BinaryIO) -> Iterator[bytes]:
    """Read an encrypted object (file-like, e.g. an S3 ``Body``); yield plaintext.

    Raises :class:`StorageError` when the object was tampered with, truncated
    or encrypted under another master key; never yields a silent partial result.
    """
    header = _read_exact(source, _HEADER_SIZE)
    if not is_encrypted(header):
        raise StorageError(_("The file is not in the expected encrypted format."))

    start = len(MAGIC)
    wrap_nonce = header[start : start + _NONCE]
    wrapped = header[start + _NONCE : start + _NONCE + KEY_SIZE + _TAG]
    key = master_key()
    try:
        file_key = aesgcm(key).decrypt(wrap_nonce, wrapped, MAGIC)
    except Exception as exc:  # InvalidTag and friends
        raise StorageError(
            _("The file could not be decrypted (wrong master key?).")
        ) from exc

    cipher = aesgcm(file_key)
    index = 0
    while True:
        frame = source.read(_FRAME_SIZE)
        if not frame:
            # The stream ended with no chunk flagged as last: the object was
            # cut. Failing beats returning half a document as if it were whole.
            raise StorageError(_("The encrypted file is truncated."))
        if len(frame) < _FRAME_SIZE:
            raise StorageError(_("The encrypted file is corrupted."))

        nonce, flag = frame[:_NONCE], frame[_NONCE : _NONCE + 1]
        (size,) = struct.unpack(">I", frame[_NONCE + 1 :])
        if flag not in (_MIDDLE, _LAST) or size > CHUNK + _TAG:
            raise StorageError(_("The encrypted file is corrupted."))

        body = _read_exact(source, size)
        aad = header + struct.pack(">I", index) + flag
        try:
            yield cipher.decrypt(nonce, body, aad)
        except Exception as exc:  # InvalidTag
            raise StorageError(
                _("The file was tampered with or corrupted: integrity check failed.")
            ) from exc

        if flag == _LAST:
            return
        index += 1


def _read_exact(source: BinaryIO, size: int) -> bytes:
    """Read exactly ``size`` bytes; S3 may return the body in slices."""
    parts = []
    missing = size
    while missing > 0:
        piece = source.read(missing)
        if not piece:
            raise StorageError(_("The encrypted file is truncated."))
        parts.append(piece)
        missing -= len(piece)
    return b"".join(parts)
