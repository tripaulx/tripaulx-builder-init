"""Client-side envelope encryption of files before they reach the bucket.

WHY CLIENT-SIDE: several S3-compatible providers have no real server-side
encryption. ``ServerSideEncryption`` may answer ``NotImplemented``, and SSE-C
(customer-provided keys) may be *accepted and ignored*: a ``GetObject`` without
any key returns the plaintext. Trusting it would be worse than not encrypting,
because the code would look safe. So files are encrypted here and the bucket
only ever sees ciphertext.

HOW: every file gets its own random 32-byte key. The content is encrypted with
AES-256-GCM under that key; the file key is in turn encrypted ("wrapped") with
the MASTER KEY (``FILE_ENCRYPTION_KEY``) and stored in the object's header.
The master key never encrypts data directly.

IN CHUNKS of 1 MiB, never all at once, so memory stays flat per download. Each
chunk has its own nonce, and its AAD carries the header, the chunk index and a
last-chunk flag. That stops what GCM alone does not: reordering chunks, mixing
chunks from another file and truncating the end (a cut stream has no chunk
flagged as last and fails instead of returning half a document).

WHAT IT PROTECTS: a leaked bucket credential, a bucket exposed by mistake, or
anyone with access to the provider's infrastructure. It does NOT protect
against a compromised application server, where the master key lives.

LOSING THE MASTER KEY MEANS LOSING THE FILES. Back it up outside the server.
"""

from .envelope import CHUNK, MAGIC, decrypt_stream, encrypt_stream, is_encrypted
from .keys import encryption_enabled, generate_master_key, master_key

__all__ = [
    "CHUNK",
    "MAGIC",
    "decrypt_stream",
    "encrypt_stream",
    "encryption_enabled",
    "generate_master_key",
    "is_encrypted",
    "master_key",
]
