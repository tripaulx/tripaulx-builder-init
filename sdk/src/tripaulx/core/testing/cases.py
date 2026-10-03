"""Base test cases for code that runs inside a tenant schema.

``FastTenantTestCase`` creates and migrates the test tenant schema once per
session; each test runs in a rolled-back transaction.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django_tenants.test.cases import FastTenantTestCase
from django_tenants.test.client import BaseTenantRequestFactory, TenantClient
from rest_framework.test import APIClient


class TenantAPIClient(BaseTenantRequestFactory, APIClient):
    """DRF ``APIClient`` whose requests go to the tenant's primary domain.

    Keeps the ``APIClient`` helpers (``credentials``, ``format="json"``,
    ``response.data``).
    """


class TenantTestCase(FastTenantTestCase):
    """Tenant schema created once, plus helpers for users and clients."""

    @classmethod
    def setup_tenant(cls, tenant: Any) -> None:
        """Fill the required fields of the test workspace."""
        tenant.name = "Test workspace"

    def make_user(
        self,
        email: str = "member@example.com",
        password: str = "test-password",
        **extra: Any,
    ) -> Any:
        """Create a user in the tenant schema (the active connection)."""
        return get_user_model().objects.create_user(
            email=email, password=password, **extra
        )

    def tenant_client(self) -> TenantClient:
        """Return a Django test client routed to the tenant's domain."""
        return TenantClient(self.tenant)


class TenantAPITestCase(TenantTestCase):
    """Tenant test case with DRF clients authenticated by schema-bound JWTs."""

    def api_client(self, user: Any = None) -> TenantAPIClient:
        """Return a client authenticated as ``user`` (a new member if None).

        The token comes from ``refresh_for``, exactly like a real login, so
        it carries the schema claim the authentication requires.
        """
        from tripaulx.accounts.services.tokens import refresh_for

        user = user if user is not None else self.make_user()
        client = TenantAPIClient(self.tenant)
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_for(user).access_token}"
        )
        return client

    def anon_api_client(self) -> TenantAPIClient:
        """Return an anonymous client routed to the tenant's domain."""
        return TenantAPIClient(self.tenant)
