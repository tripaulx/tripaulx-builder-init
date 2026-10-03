"""Base ``ModelAdmin`` for projects to register their concrete user with."""

from __future__ import annotations

from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _


class TripaulxUserAdmin(UserAdmin):
    """User admin keyed by e-mail, with role and security flags.

    Projects register it explicitly: ``admin.site.register(User,
    TripaulxUserAdmin)``.
    """

    ordering = ("email",)
    list_display = ("email", "role", "is_active", "email_verified", "is_staff")
    list_filter = ("role", "is_active", "email_verified", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (_("Workspace"), {"fields": ("role",)}),
        (_("Security"), {"fields": ("email_verified", "password_login_disabled")}),
        (
            _("Permissions"),
            {"fields": ("is_active", "is_staff", "is_superuser", "groups")},
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
