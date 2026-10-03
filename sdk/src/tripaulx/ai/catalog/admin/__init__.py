"""Admin of the shared model catalog (public-schema admin)."""

from typing import Any

from django.contrib import admin
from django.db import connection
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django_tenants.utils import get_public_schema_name

from ..models import AIModel


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    """The catalog. ``identifier`` must match the provider's model name."""

    list_display = (
        "label",
        "identifier",
        "provider",
        "active",
        "highlighted",
        "recommended",
        "order",
        "input_price_usd_1m",
        "output_price_usd_1m",
    )
    list_editable = ("active", "highlighted", "order")
    list_filter = ("provider", "active", "supports_reasoning", "cost_tier")
    search_fields = ("label", "identifier", "description")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            None,
            {"fields": ("provider", "identifier", "label", "description", "active")},
        ),
        (
            _("Presentation"),
            {
                "fields": (
                    "order",
                    "highlighted",
                    "recommended",
                    "nickname",
                    "cost_tier",
                )
            },
        ),
        (
            _("Call parameters"),
            {
                "fields": (
                    "supports_reasoning",
                    "accepts_minimal_effort",
                    "uses_thinking_budget",
                    "options",
                )
            },
        ),
        (
            _("Prices"),
            {
                "fields": (
                    "input_price_usd_1m",
                    "cached_price_usd_1m",
                    "output_price_usd_1m",
                    "prices_updated_on",
                )
            },
        ),
        (_("Dates"), {"fields": ("created_at", "updated_at")}),
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Only the public-schema admin edits the shared catalog."""
        return _on_public() and super().has_add_permission(request)

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Workspace admins see the catalog read-only."""
        return _on_public() and super().has_change_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Workspace admins never delete shared rows."""
        return _on_public() and super().has_delete_permission(request, obj)


def _on_public() -> bool:
    """Whether the current connection is on the public schema."""
    return connection.schema_name == get_public_schema_name()
