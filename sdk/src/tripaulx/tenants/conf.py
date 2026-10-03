"""Defaults for the tenants app, overridable through ``settings.TRIPAULX``."""

from tripaulx.core.conf import AppSettings

app_settings = AppSettings(
    {
        # Apex domain; each workspace is served at ``<slug>.<BASE_DOMAIN>``.
        "BASE_DOMAIN": "localhost",
        # Extra hostnames served by the public schema (besides apex and www).
        "PUBLIC_DOMAINS": (),
        # Workspace created by ``bootstrap_workspace`` when no --schema is given.
        # Empty means "only the public schema".
        "BOOTSTRAP_WORKSPACE": "",
        "BOOTSTRAP_WORKSPACE_NAME": "",
        # Project-specific labels that can never become workspace slugs.
        "EXTRA_RESERVED_SLUGS": (),
    }
)
