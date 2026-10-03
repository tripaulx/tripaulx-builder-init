"""Workspace: the tenant, mapped 1:1 to a PostgreSQL schema."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_tenants.models import TenantMixin


class Workspace(TenantMixin):
    """A customer workspace with its own isolated schema.

    The schema is created on first save (``auto_create_schema``).
    ``schema_name`` doubles as the workspace slug used in its subdomain.
    """

    name = models.CharField(_("name"), max_length=100)
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    auto_create_schema = True

    class Meta:
        verbose_name = _("workspace")
        verbose_name_plural = _("workspaces")
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
