"""Admin of the Mailgun singleton: the API key is write-only."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.db import connection
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django_tenants.utils import get_public_schema_name

from ..models import MailgunConfig


class MailgunConfigForm(forms.ModelForm):
    """Hide the API key; store a new one only when the field is filled."""

    new_api_key = forms.CharField(
        label=_("New API key (leave blank to keep the current one)"),
        widget=forms.PasswordInput(render_value=False),
        required=False,
        strip=True,
    )

    class Meta:
        model = MailgunConfig
        fields = (
            "enabled",
            "domain",
            "region",
            "default_from_email",
            "default_from_name",
        )

    def save(self, commit: bool = True) -> MailgunConfig:
        """Encrypt the new key, if any, before saving."""
        instance = super().save(commit=False)
        new_key = self.cleaned_data.get("new_api_key")
        if new_key:
            instance.api_key = new_key
        if commit:
            instance.save()
        return instance


@admin.register(MailgunConfig)
class MailgunConfigAdmin(admin.ModelAdmin):
    """Single-row admin; it can neither add a second row nor delete it."""

    form = MailgunConfigForm
    list_display = ("__str__", "enabled", "domain", "region", "updated_at")
    readonly_fields = ("api_key_status", "updated_at")
    fields = (
        "enabled",
        "domain",
        "region",
        "default_from_email",
        "default_from_name",
        "new_api_key",
        "api_key_status",
        "updated_at",
    )

    @admin.display(description=_("API key"))
    def api_key_status(self, obj: MailgunConfig | None) -> str:
        """Say whether a key is stored, never showing it."""
        if obj is not None and obj.api_key:
            return str(_("•••• set"))
        return str(_("not set"))

    def has_module_permission(self, request: HttpRequest) -> bool:
        """Show the configuration only in the public schema's admin."""
        on_public = connection.schema_name == get_public_schema_name()
        return on_public and super().has_module_permission(request)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Allow viewing only in the public schema, where the table lives."""
        on_public = connection.schema_name == get_public_schema_name()
        return on_public and super().has_view_permission(request, obj)

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Allow adding only while the singleton does not exist."""
        if connection.schema_name != get_public_schema_name():
            return False
        return not MailgunConfig.objects.exists()

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Never delete the singleton."""
        return False
