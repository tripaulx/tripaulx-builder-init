"""Installed apps: SDK defaults plus the project's own apps.

The ``users`` app defines ``AUTH_USER_MODEL`` and must be in both lists.
Add tenant-only business apps to ``PROJECT_TENANT_APPS``.
"""

from tripaulx.settings import apps as sdk_apps

PROJECT_SHARED_APPS = ("users",)
PROJECT_TENANT_APPS = ("users",)

SHARED_APPS = sdk_apps.shared_apps(*PROJECT_SHARED_APPS)
TENANT_APPS = sdk_apps.tenant_apps(*PROJECT_TENANT_APPS)
INSTALLED_APPS = sdk_apps.installed_apps(SHARED_APPS, TENANT_APPS)

TENANT_MODEL = sdk_apps.TENANT_MODEL
TENANT_DOMAIN_MODEL = sdk_apps.TENANT_DOMAIN_MODEL
DATABASE_ROUTERS = sdk_apps.DATABASE_ROUTERS
PUBLIC_SCHEMA_NAME = sdk_apps.PUBLIC_SCHEMA_NAME
SHOW_PUBLIC_IF_NO_TENANT_FOUND = sdk_apps.SHOW_PUBLIC_IF_NO_TENANT_FOUND
TENANT_CREATION_FAKES_MIGRATIONS = sdk_apps.TENANT_CREATION_FAKES_MIGRATIONS
