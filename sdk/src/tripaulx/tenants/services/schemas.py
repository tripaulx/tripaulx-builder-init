"""Schema names of the workspaces, for jobs that visit every one of them."""

from __future__ import annotations

from django_tenants.utils import (
    get_public_schema_name,
    get_tenant_model,
    schema_context,
)


def workspace_schemas() -> list[str]:
    """Return the schema of every workspace (the public schema excluded)."""
    with schema_context(get_public_schema_name()):
        return list(
            get_tenant_model()
            .objects.exclude(schema_name=get_public_schema_name())
            .values_list("schema_name", flat=True)
        )
