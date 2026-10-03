"""Admin of the AI settings (singleton) with a write-only key field.

A new key goes through the SAME service as the API
(:mod:`tripaulx.ai.services.keys`), so the actor is recorded. The key is
never displayed: only its state (who added it, when).
"""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from tripaulx.ai import providers
from tripaulx.ai.models import AISettings
from tripaulx.ai.services import keys
from tripaulx.ai.services.model_choice import InvalidModelChoice, check


class AISettingsForm(forms.ModelForm):
    """Settings form: provider select, catalog check, optional new key."""

    provider = forms.ChoiceField(label=_("provider"), choices=())
    new_api_key = forms.CharField(
        label=_("New API key of the chosen provider (blank keeps the current one)"),
        widget=forms.PasswordInput(render_value=False),
        required=False,
        strip=True,
        help_text=_(
            "Stored encrypted and never shown again; replaces the current key."
        ),
    )
    delete_api_key = forms.BooleanField(
        label=_("Delete the current key of the chosen provider"), required=False
    )

    class Meta:
        model = AISettings
        fields = (
            "enabled",
            "provider",
            "model_identifier",
            "effort",
            "max_output_tokens",
            "daily_cap_usd",
            "store_content",
            "retention_days",
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Fill the provider choices from the registry."""
        super().__init__(*args, **kwargs)
        self.fields["provider"].choices = providers.choices()

    def clean_new_api_key(self) -> str:
        """Refuse a key that would not fit in an HTTP header."""
        value = self.cleaned_data.get("new_api_key") or ""
        if value:
            try:
                keys.validate(self.data.get("provider") or "openai", value)
            except keys.InvalidKey as exc:
                raise ValidationError(str(exc)) from exc
        return value

    def clean(self) -> dict[str, Any]:
        """One key action at a time; the model must fit the provider."""
        data = super().clean()
        if data.get("new_api_key") and data.get("delete_api_key"):
            raise ValidationError(
                gettext("Choose one: add a new key OR delete the current one.")
            )
        try:
            check(data.get("model_identifier") or "", data.get("provider"))
        except InvalidModelChoice as exc:
            self.add_error("model_identifier", str(exc))
        return data


@admin.register(AISettings)
class AISettingsAdmin(admin.ModelAdmin):
    """Singleton per workspace: no second row, no deletion."""

    form = AISettingsForm
    list_display = ("__str__", "enabled", "provider", "model_identifier", "updated_at")
    readonly_fields = ("api_key_status", "updated_at")
    fieldsets = (
        (None, {"fields": ("enabled", "provider", "model_identifier")}),
        (_("API key"), {"fields": ("new_api_key", "delete_api_key", "api_key_status")}),
        (_("Call defaults"), {"fields": ("effort", "max_output_tokens")}),
        (
            _("Limits and privacy"),
            {"fields": ("daily_cap_usd", "store_content", "retention_days")},
        ),
        (_("Dates"), {"fields": ("updated_at",)}),
    )

    @admin.display(description=_("API key"))
    def api_key_status(self, obj: AISettings | None) -> str:
        """Who added the key of the chosen provider and when (never the value)."""
        key = keys.active(obj.provider) if obj else None
        if key is None:
            return gettext("not set")
        state = {
            "when": f"{key.created_at:%Y-%m-%d %H:%M}",
            "who": key.created_by_label,
        }
        if key.readable:
            return gettext("set on %(when)s by %(who)s") % state
        # A stored token that no longer decrypts: the field key was rotated.
        return (
            gettext("stored on %(when)s by %(who)s, but unreadable: add it again")
            % state
        )

    def save_model(
        self, request: HttpRequest, obj: AISettings, form: Any, change: bool
    ) -> None:
        """Save, then apply the key action through the service."""
        super().save_model(request, obj, form, change)
        if form.cleaned_data.get("new_api_key"):
            keys.add(obj.provider, form.cleaned_data["new_api_key"], by=request.user)
        elif form.cleaned_data.get("delete_api_key"):
            keys.delete(obj.provider, by=request.user)

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Only while the singleton does not exist."""
        return not AISettings.objects.exists()

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Refuse deletion: the singleton stays."""
        return False
