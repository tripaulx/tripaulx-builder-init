"""Middleware provided by the core app."""

from .tenant import TenantMiddleware

__all__ = ["TenantMiddleware"]
