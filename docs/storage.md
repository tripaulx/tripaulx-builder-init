# Object storage (`tripaulx.storage`)

Private, S3-compatible object storage for multi-tenant projects:

- every object key lives under `tenants/<schema>/`, and keys of another tenant are refused;
- files are encrypted on the application side before upload (envelope encryption, AES-256-GCM);
- uploads go through a configurable policy: MIME allowlist checked against magic bytes, byte limits and an image pixel limit.

It works with AWS S3 and with S3-compatible providers (path-style addressing, SigV4).

## Install

The app is in the SDK's default app lists. Its runtime dependencies are an optional extra:

```bash
uv add "tripaulx-sdk[storage]"   # boto3, cryptography, pillow
```

Importing `tripaulx.storage` never needs them. Using the client without them raises `ImproperlyConfigured` with the install command.

## Settings

All options live in `settings.TRIPAULX`. The project template maps them from environment variables in `config/settings/base_parts/object_storage.py`.

| Key | Env (template) | Default | Meaning |
|---|---|---|---|
| `S3_ENABLED` | set when both keys exist | `False` | Off: every call raises `StorageError` |
| `S3_ENDPOINT_URL` | `APP_S3_ENDPOINT_URL` | `""` | Provider endpoint (empty = AWS) |
| `S3_REGION` | `APP_S3_REGION` | `""` | Region of the bucket |
| `S3_BUCKET` | `APP_S3_BUCKET` | `""` | Private bucket name |
| `S3_ACCESS_KEY` | `APP_S3_ACCESS_KEY` | `""` | Access key id |
| `S3_SECRET_KEY` | `APP_S3_SECRET_KEY` | `""` | Secret key |
| `S3_URL_TTL` | `APP_S3_URL_TTL` | `900` | Presigned link lifetime, in seconds |
| `MAX_UPLOAD_BYTES` | `APP_S3_MAX_UPLOAD_BYTES` | 25 MiB | Limit of `upload` |
| `MAX_IMAGE_BYTES` | `APP_S3_MAX_IMAGE_BYTES` | 2 MiB | Limit of `upload_image` |
| `MAX_IMAGE_PIXELS` | `APP_S3_MAX_IMAGE_PIXELS` | 4,000,000 | Width x height of any image |
| `FILE_ENCRYPTION_KEY` | `APP_FILE_ENCRYPTION_KEY` | `""` | Master key; empty stores files in clear |
| `ALLOWED_TYPES` | (Python only) | PDF, PNG, JPEG, WebP | Upload policy, see below |

> **Point the region at the bucket's real region.** A wrong region usually fails as `NoSuchBucket`, not as a credential error.

## Usage

```python
from tripaulx.storage import services as storage

key = storage.build_key("invoices", str(invoice.pk), name=uploaded.name)
# StoredFile(key, name, size, content_type, encrypted)
stored = storage.upload(uploaded, key)

# Serve it: stream through the app (works for encrypted and clear objects) ...
response = StreamingHttpResponse(
    storage.download(stored.key), content_type=stored.content_type
)
# ... or, for objects stored in clear, hand out a presigned link.
url = storage.temporary_url(
    stored.key, download_name="Invoice.pdf", content_type="application/pdf"
)

storage.delete(stored.key)
```

| Function | What it does |
|---|---|
| `build_key(*parts, name=)` | `tenants/<schema>/<parts>/<random>-<clean name>` for the active schema |
| `clean_name(name)` | Strips paths and accents, keeps `[A-Za-z0-9._-]` |
| `upload(file, key, content_type="", *, types=None, max_bytes=None)` | Validates, then uploads (encrypted when a master key is set). `types` narrows the policy for one call and never widens it |
| `upload_image(file, key, content_type="")` | Same, limited to the `image/*` policy types and `MAX_IMAGE_BYTES` |
| `download(key)` | Iterator of plaintext chunks; decrypts encrypted objects, returns clear ones as they are |
| `temporary_url(key, *, download_name="", content_type="")` | Presigned GET link, valid `S3_URL_TTL` seconds |
| `delete(key)` | Removes the object |
| `content_disposition(name, content_type)` | `inline` for `INLINE_TYPES`, `attachment` otherwise |

Every function that takes a key first checks that it belongs to the active tenant (`ensure_tenant_key`). All failures raise `StorageError`, with a translated message that is safe to show to users.

Keep the real `content_type` in your own model. With encryption on, the object in the bucket is stored as `application/octet-stream`.

## Upload policy

`ALLOWED_TYPES` maps each accepted MIME type to the signatures its content must carry. Each signature is an `(offset, bytes)` pair, and every pair must match. An offset of `None` means "anywhere in the first 1024 bytes". This handles PDFs that scanners and signing tools write with a preamble.

```python
from tripaulx.storage.conf import DEFAULT_ALLOWED_TYPES

TRIPAULX = {
    # ...
    "ALLOWED_TYPES": {
        **DEFAULT_ALLOWED_TYPES,
        "image/gif": ((0, b"GIF8"),),
    },
}
```

The declared content type comes from the client and proves nothing, so the signature is always checked. Images (`image/*`) are also opened with Pillow, which reads only the header, and refused above `MAX_IMAGE_PIXELS`. This stops decompression bombs: a flat-colour PNG of 12000x12000 pixels fits in a few hundred KB.

Never allow SVG or HTML. Both can carry scripts, and served inline from your domain they become cross-site scripting.

## Encryption

Some S3-compatible providers have no real server-side encryption, and some accept SSE-C keys and silently ignore them. The SDK therefore encrypts on the application side:

1. Each file gets a random 32-byte key.
2. The content is encrypted with AES-256-GCM in 1 MiB chunks, each with its own nonce.
3. Each chunk's AAD is the header, the chunk index and a last-chunk flag. Reordered, mixed or truncated objects fail instead of returning partial data.
4. The file key is wrapped with the master key (`FILE_ENCRYPTION_KEY`) and stored in the object header, which starts with the marker `TPX1\0`.

Downloads fall back to plaintext for objects without the marker, for example files uploaded before a key was set.

This protects against a leaked bucket credential, a bucket exposed by mistake and the provider's own staff. It does not protect against a compromised application server, where the master key lives.

```bash
uv run python manage.py generate_file_key
```

> **Losing the master key means losing every encrypted file.** Keep a backup outside the server, for example in a password manager. `./start` generates a local key in `.env.local`. In production, set `APP_FILE_ENCRYPTION_KEY` in the CapRover app.

## Smoke test

```bash
uv run python manage.py check_bucket --schema acme [--keep]
```

`check_bucket` runs a real cycle against the provider: it uploads a test object, creates a presigned link, downloads through it and deletes the object. With encryption on, it also proves two things: the stored bytes are unreadable, and the application decrypts them back. Run it after setting credentials. A mocked test cannot catch provider quirks such as rejected checksums.

## Tests

Tests never talk to the network. Mock `tripaulx.storage.client.get_client`, as the SDK suite does. The template's `tests/conftest.py` disables storage and blanks the file key for every test, so the result never depends on `.env.local`.
