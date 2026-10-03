"""Base test case for code that runs inside a tenant schema.

``FastTenantTestCase`` creates and migrates the test tenant schema once per
session; each test runs in a rolled-back transaction.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django_tenants.test.cases import FastTenantTestCase
from django_tenants.test.client import TenantClient


class TenantTestCase(FastTenantTestCase):
    """Tenant schema created once, plus helpers for users and clients."""

    @classmethod
    def setup_tenant(cls, tenant: Any) -> None:
        """Fill the required fields of the test workspace."""
        tenant.name = "Test workspace"

    def make_user(
        self, email: str = "member@example.com", password: str = "test-password"
    ) -> Any:
        """Create a user in the tenant schema (the active connection)."""
        return get_user_model().objects.create_user(email=email, password=password)

    def tenant_client(self) -> TenantClient:
        """Return a Django test client routed to the tenant's domain."""
        return TenantClient(self.tenant)
