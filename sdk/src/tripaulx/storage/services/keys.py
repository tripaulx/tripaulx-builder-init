"""Object keys, always inside the current tenant's prefix.

TENANT ISOLATION: every key starts with ``tenants/<schema>/`` and the schema
always comes from the active connection (``connection.schema_name``), never
from anything the client sends. A tenant cannot name an object inside another
tenant's prefix, by accident or on purpose.
"""

from __future__ import annotations

from pathlib import PurePosixPath
import re
import unicodedata
import uuid

from django.db import connection
from django.utils.translation import gettext as _

from ..exceptions import StorageError

#: Characters kept in a file name inside a key; anything else becomes "-".
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")

#: Longest file name kept in a key.
MAX_NAME_LENGTH = 120


def tenant_prefix() -> str:
    """Return the prefix of every key of the current tenant."""
    return f"tenants/{connection.schema_name}"


def clean_name(name: str) -> str:
    """Reduce a file name to something safe to embed in a key.

    Strips accents, replaces anything outside ``[A-Za-z0-9._-]`` with ``-`` and
    drops any path component: ``../../etc/passwd`` becomes ``passwd`` and
    never escapes the tenant prefix.
    """
    base = PurePosixPath(name.replace("\\", "/")).name
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    base = _UNSAFE.sub("-", base).strip("-.") or "file"
    return base[:MAX_NAME_LENGTH]


def build_key(*parts: str, name: str) -> str:
    """Build the full key of an object, always inside the current tenant.

    A random id precedes the name so two files with the same name never
    overwrite each other.
    """
    path = "/".join(_UNSAFE.sub("-", part.strip("/")) for part in parts if part)
    prefix = f"{tenant_prefix()}/{path}" if path else tenant_prefix()
    return f"{prefix}/{uuid.uuid4().hex[:12]}-{clean_name(name)}"


def ensure_tenant_key(key: str) -> None:
    """Refuse any key outside the current tenant's prefix.

    Last line of defence: even if a key arrives tampered with (from the
    database or a parameter), no link is signed and nothing is read or deleted
    for ANOTHER tenant.
    """
    if not key.startswith(f"{tenant_prefix()}/") or ".." in key.split("/"):
        raise StorageError(_("The file is outside this tenant's scope."))
