"""Read-only admins: key history and events."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from tripaulx.ai.models import AIEvent, AIKey


class ReadOnlyAdmin(admin.ModelAdmin):
    """No add, change or delete: rows are an audit trail."""

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> list[str]:
        """Every field is read-only."""
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Rows are created by the services only."""
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Rows are immutable."""
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Rows are never deleted here."""
        return False


@admin.register(AIKey)
class AIKeyAdmin(ReadOnlyAdmin):
    """Key history. Adding and deleting keys is done in the settings."""

    list_display = (
        "provider",
        "created_at",
        "created_by_label",
        "closed_at",
        "closed_by_label",
        "closed_reason",
    )
    list_filter = ("provider", "closed_reason")
    exclude = ("api_key_encrypted",)

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> list[str]:
        """Every field but the encrypted token, which is never shown."""
        return [
            f
            for f in super().get_readonly_fields(request, obj)
            if f != "api_key_encrypted"
        ]


@admin.register(AIEvent)
class AIEventAdmin(ReadOnlyAdmin):
    """The lens to investigate one call."""

    list_display = (
        "created_at",
        "agent_label",
        "step",
        "origin",
        "model_identifier",
        "status",
        "error_code",
        "latency_ms",
        "total_tokens",
        "cost_usd",
    )
    list_filter = ("origin", "status", "provider", "error_code", "step")
    search_fields = ("reference", "execution_id", "agent_label", "user_label")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
