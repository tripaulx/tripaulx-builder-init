"""Admin registrations of the tenants app (public schema only)."""

from .workspace import DomainAdmin, DomainInline, WorkspaceAdmin

__all__ = ["DomainAdmin", "DomainInline", "WorkspaceAdmin"]
