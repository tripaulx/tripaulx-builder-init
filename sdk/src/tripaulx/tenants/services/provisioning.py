"""Create a workspace end to end: row, schema, domain and initial data.

Everything runs in one transaction. PostgreSQL DDL is transactional, so if
the setup step fails (e.g. the owner cannot be created) the schema and its
tables disappear together with the workspace row.

Creating a schema runs every tenant migration, which takes a few seconds; the
call is synchronous.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _
from django_tenants.utils import schema_context

from ..models import Domain, Workspace
from ..signals import workspace_created
from ..validators.slug import validate_workspace_slug
from .domains import workspace_domain
from .slugs import is_slug_available

Setup = Callable[[Workspace], Any]


def _taken() -> ValidationError:
    """Error for a slug that already belongs to a workspace."""
    return ValidationError(_("This address is already taken."), code="slug_taken")


def provision_workspace(
    name: str, slug: str, setup: Setup | None = None
) -> tuple[Workspace, Any]:
    """Create the workspace ``slug`` and run ``setup`` inside its schema.

    Must be called from the public schema. Returns ``(workspace, result)``
    where ``result`` is what ``setup`` returned.

    Raises:
        ValidationError: invalid, reserved or taken slug.
    """
    validate_workspace_slug(slug)
    if not is_slug_available(slug):
        raise _taken()
    try:
        with transaction.atomic():
            workspace = Workspace(schema_name=slug, name=name)
            workspace.save(verbosity=0)
            domain = Domain.objects.create(
                domain=workspace_domain(slug), tenant=workspace, is_primary=True
            )
            with schema_context(slug):
                result = setup(workspace) if setup is not None else None
    except IntegrityError as exc:
        raise _taken() from exc
    transaction.on_commit(
        lambda: workspace_created.send(
            sender=Workspace, workspace=workspace, domain=domain, result=result
        )
    )
    return workspace, result
