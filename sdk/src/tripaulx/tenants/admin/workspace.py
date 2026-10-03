"""Admin for workspaces and their domains."""

from __future__ import annotations

from django.contrib import admin
from django_tenants.admin import TenantAdminMixin

from ..models import Domain, Workspace


class DomainInline(admin.TabularInline):
    """Domains edited inside their workspace."""

    model = Domain
    extra = 0
    fields = ("domain", "is_primary")


@admin.register(Workspace)
class WorkspaceAdmin(TenantAdminMixin, admin.ModelAdmin):
    """Workspace list with search by name and schema."""

    list_display = ("name", "schema_name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "schema_name")
    readonly_fields = ("created_at", "updated_at")
    inlines = (DomainInline,)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    """Flat list of every hostname and its workspace."""

    list_display = ("domain", "tenant", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("domain", "tenant__schema_name")
