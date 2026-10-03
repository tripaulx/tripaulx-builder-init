"""Read-only admin of the security records (codes, devices, passkeys).

Secrets never show: codes and tokens are hashes, the TOTP secret is
encrypted. Deleting a TOTP device is the way out for a user who lost both
the phone and the recovery codes: the login falls back to e-mail codes.
"""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from ..models import (
    EmailCode,
    Invitation,
    RecoveryCode,
    TotpDevice,
    TrustedDevice,
    WebAuthnCredential,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    """No add and no change; deletion stays available."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Refuse: records are created by the account flows only."""
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Refuse: records are never edited by hand."""
        return False


@admin.register(EmailCode)
class EmailCodeAdmin(ReadOnlyAdmin):
    """E-mail codes (hash only)."""

    list_display = ("user", "purpose", "expires_at", "attempts", "consumed_at")
    list_filter = ("purpose",)
    search_fields = ("user__email",)
    exclude = ("code_hash",)


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(ReadOnlyAdmin):
    """Recovery codes; the plain text never exists after generation."""

    list_display = ("prefix", "user", "label", "created_at", "used_at")
    list_filter = ("used_at",)
    search_fields = ("user__email", "prefix", "label")
    exclude = ("code_hash",)


@admin.register(WebAuthnCredential)
class WebAuthnCredentialAdmin(ReadOnlyAdmin):
    """Passkeys."""

    list_display = ("name", "user", "sign_count", "created_at", "last_used_at")
    search_fields = ("user__email", "name", "credential_id")


@admin.register(TotpDevice)
class TotpDeviceAdmin(ReadOnlyAdmin):
    """Authenticator apps (the encrypted secret is hidden)."""

    list_display = ("user", "confirmed_at", "created_at", "last_used_at")
    list_filter = ("confirmed_at",)
    search_fields = ("user__email",)
    exclude = ("secret_encrypted",)


@admin.register(TrustedDevice)
class TrustedDeviceAdmin(ReadOnlyAdmin):
    """Trusted devices (the token hash is hidden)."""

    list_display = ("user", "device_label", "ip_address", "expires_at", "is_active")
    list_filter = ("is_active",)
    search_fields = ("user__email", "device_label")
    exclude = ("token_hash",)


@admin.register(Invitation)
class InvitationAdmin(ReadOnlyAdmin):
    """Invitations (the token hash is hidden)."""

    list_display = ("email", "role", "invited_by", "expires_at", "accepted_at")
    list_filter = ("role",)
    search_fields = ("email",)
    exclude = ("token_hash",)
