"""Installed-app lists and django-tenants routing for projects using the SDK.

Rules:

1. ``django_tenants`` comes first and the tenant app sits in ``SHARED_APPS``.
2. The app defining ``AUTH_USER_MODEL`` must be in **both** lists: each schema
   holds its own users, and foreign keys cannot cross schemas.
3. ``INSTALLED_APPS`` is ``SHARED_APPS`` plus the tenant-only apps, in order.
"""

from __future__ import annotations

from collections.abc import Iterable

_CONTRIB_APPS = (
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
)

SDK_SHARED_APPS: tuple[str, ...] = (
    "django_tenants",
    "tripaulx.tenants",
    *_CONTRIB_APPS,
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "tripaulx.core",
    "tripaulx.accounts",
    # Outstanding/blacklisted refresh tokens point at the user, so they live
    # in every schema that holds users.
    "rest_framework_simplejwt.token_blacklist",
    # Global e-mail configuration: one row in the public schema only.
    "tripaulx.mail",
    "tripaulx.storage",
)

SDK_TENANT_APPS: tuple[str, ...] = (
    *_CONTRIB_APPS,
    "tripaulx.core",
    "tripaulx.accounts",
    "rest_framework_simplejwt.token_blacklist",
    "tripaulx.storage",
)

TENANT_MODEL = "tpsdk_tenants.Workspace"
TENANT_DOMAIN_MODEL = "tpsdk_tenants.Domain"
DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)
PUBLIC_SCHEMA_NAME = "public"
SHOW_PUBLIC_IF_NO_TENANT_FOUND = False
TENANT_CREATION_FAKES_MIGRATIONS = False


def _merge(base: Iterable[str], extra: Iterable[str]) -> tuple[str, ...]:
    """Concatenate two app lists, dropping duplicates while keeping order."""
    return tuple(dict.fromkeys((*base, *extra)))


def shared_apps(*project_apps: str) -> tuple[str, ...]:
    """Return the SDK shared apps followed by ``project_apps``."""
    return _merge(SDK_SHARED_APPS, project_apps)


def tenant_apps(*project_apps: str) -> tuple[str, ...]:
    """Return the SDK tenant apps followed by ``project_apps``."""
    return _merge(SDK_TENANT_APPS, project_apps)


def installed_apps(shared: Iterable[str], tenant: Iterable[str]) -> list[str]:
    """Combine shared and tenant apps into ``INSTALLED_APPS``."""
    return list(_merge(shared, tenant))
