"""Domain: a hostname that resolves to a workspace."""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from django_tenants.models import DomainMixin


class Domain(DomainMixin):
    """Hostname routed to a workspace; one per workspace is primary."""

    class Meta:
        verbose_name = _("domain")
        verbose_name_plural = _("domains")
        ordering = ("domain",)

    def __str__(self) -> str:
        return self.domain
