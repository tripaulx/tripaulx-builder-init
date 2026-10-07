"""Admin mixins that keep a model to the schemas where its table exists.

The admin registry is global, but django-tenants creates each app's tables in
the public schema, in the workspace schemas, or in both. A ModelAdmin of a
workspace-only app shown in the public admin (or the reverse) makes the admin
index fail as soon as one permission check queries its table. These mixins
answer every permission with ``False`` outside the right schema, before any
query, so the model is simply absent there.
"""

from __future__ import annotations

from typing import Any

from django.db import connection
from django.http import HttpRequest
from django_tenants.utils import get_public_schema_name


def on_public_schema() -> bool:
    """Whether the current request runs on the public schema."""
    return connection.schema_name == get_public_schema_name()


class _SchemaScopedAdmin:
    """Deny every permission when :meth:`in_scope` is false."""

    @staticmethod
    def in_scope() -> bool:
        """Whether the model's table exists in the current schema."""
        raise NotImplementedError

    def has_module_permission(self, request: HttpRequest) -> bool:
        """Hide the app outside its schemas."""
        return self.in_scope() and super().has_module_permission(request)  # type: ignore[misc]

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Refuse viewing outside its schemas."""
        return self.in_scope() and super().has_view_permission(request, obj)  # type: ignore[misc]

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        """Refuse adding outside its schemas (``*args``: inline admins' obj)."""
        return self.in_scope() and super().has_add_permission(request, *args)  # type: ignore[misc]

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Refuse changing outside its schemas."""
        return self.in_scope() and super().has_change_permission(request, obj)  # type: ignore[misc]

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Refuse deleting outside its schemas."""
        return self.in_scope() and super().has_delete_permission(request, obj)  # type: ignore[misc]


class PublicSchemaAdmin(_SchemaScopedAdmin):
    """For models of shared-only apps (tables in the public schema)."""

    @staticmethod
    def in_scope() -> bool:
        """Only on the public schema."""
        return on_public_schema()


class WorkspaceSchemaAdmin(_SchemaScopedAdmin):
    """For models of workspace-only apps (tables in every workspace schema)."""

    @staticmethod
    def in_scope() -> bool:
        """Only on workspace schemas."""
        return not on_public_schema()
