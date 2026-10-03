"""Reading and deleting objects: download, presigned link, delete.

TWO READ PATHS, and the difference matters:

* A file stored IN CLEAR can be fetched by the browser straight from the
  bucket through a presigned link that expires (:func:`temporary_url`); it
  never goes through the application server.
* An ENCRYPTED file has no possible link: the bucket only holds ciphertext and
  only the server has the key. The download goes through the application
  (:func:`download`), which reads and decrypts it as a stream.
"""

from __future__ import annotations

from collections.abc import Iterator

from django.utils.translation import gettext as _

from .. import client, crypto
from ..conf import app_settings
from ..exceptions import StorageError
from .keys import ensure_tenant_key
from .policy import content_disposition
from .streams import PeekedStream


def download(key: str) -> Iterator[bytes]:
    """Yield the object's content IN CLEAR, chunk by chunk.

    Encrypted objects are decrypted on the fly; objects stored in clear (for
    example uploaded while no master key was set) are returned as they are.
    """
    ensure_tenant_key(key)
    try:
        response = client.get_client().get_object(
            Bucket=app_settings.S3_BUCKET, Key=key
        )
    except StorageError:
        raise
    except Exception as exc:
        raise StorageError(
            _("Failed to read the file: %(error)s") % {"error": exc}
        ) from exc

    body = response["Body"]
    peeked = body.read(len(crypto.MAGIC))
    if crypto.is_encrypted(peeked):
        yield from crypto.decrypt_stream(PeekedStream(peeked, body))
        return

    # Plaintext fallback: the peek already consumed the first bytes.
    yield peeked
    while piece := body.read(crypto.CHUNK):
        yield piece


def temporary_url(key: str, *, download_name: str = "", content_type: str = "") -> str:
    """Return a presigned read URL valid for ``S3_URL_TTL`` seconds.

    The bucket is private: without this signature the object does not open.
    ``download_name`` travels with the file and ``content_type`` decides
    whether it opens in the tab or downloads (see ``content_disposition``).
    Only meaningful for objects stored in clear.
    """
    ensure_tenant_key(key)
    params = {"Bucket": app_settings.S3_BUCKET, "Key": key}
    if download_name:
        params["ResponseContentDisposition"] = content_disposition(
            download_name, content_type
        )
    if content_type:
        params["ResponseContentType"] = content_type
    try:
        return client.get_client().generate_presigned_url(
            "get_object", Params=params, ExpiresIn=app_settings.S3_URL_TTL
        )
    except StorageError:
        raise
    except Exception as exc:
        raise StorageError(
            _("Failed to create the file link: %(error)s") % {"error": exc}
        ) from exc


def delete(key: str) -> None:
    """Remove the object from the bucket."""
    ensure_tenant_key(key)
    try:
        client.get_client().delete_object(Bucket=app_settings.S3_BUCKET, Key=key)
    except StorageError:
        raise
    except Exception as exc:
        raise StorageError(
            _("Failed to delete the file: %(error)s") % {"error": exc}
        ) from exc
