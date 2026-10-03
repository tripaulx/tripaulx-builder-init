"""Public API of the storage app: tenant-scoped uploads, downloads and links.

Usage::

    from tripaulx.storage import services as storage

    key = storage.build_key("invoices", str(invoice.pk), name=upload.name)
    stored = storage.upload(upload, key)
    for chunk in storage.download(stored.key):
        ...
"""

from ..exceptions import StorageError
from .access import delete, download, temporary_url
from .keys import build_key, clean_name, ensure_tenant_key, tenant_prefix
from .policy import INLINE_TYPES, SIGNATURE_WINDOW, content_disposition
from .upload import StoredFile, upload, upload_image

__all__ = [
    "INLINE_TYPES",
    "SIGNATURE_WINDOW",
    "StorageError",
    "StoredFile",
    "build_key",
    "clean_name",
    "content_disposition",
    "delete",
    "download",
    "ensure_tenant_key",
    "temporary_url",
    "tenant_prefix",
    "upload",
    "upload_image",
]
