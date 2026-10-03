"""Django REST Framework, SimpleJWT and drf-spectacular defaults.

Projects call these helpers from a ``base_parts/rest.py`` settings chunk::

    REST_FRAMEWORK = rest_framework()
    SIMPLE_JWT = simple_jwt(get_env("JWT_SIGNING_KEY", ""))
    SPECTACULAR_SETTINGS = spectacular("Acme API")
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

#: Default authentication: SimpleJWT plus the tenant (schema) check. A token
#: issued in one workspace is never valid in another one.
JWT_AUTHENTICATION = "tripaulx.accounts.api.authentication.TenantJWTAuthentication"

#: Rates of every throttle scope used by the SDK.
THROTTLE_RATES: dict[str, str] = {
    "anon": "100/hour",
    "user": "1000/hour",
    # Authentication: tight limits against brute force and e-mail spam.
    "auth_login": "10/min",
    "auth_register": "5/min",
    "auth_otp": "10/min",
    # Access-token refresh has its own bucket: in the shared "anon" bucket a
    # whole office behind one IP would exhaust it and get logged out. The
    # refresh token is unguessable, so this only contains abuse.
    "auth_refresh": "60/min",
}


def _merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge ``overrides`` into ``base``; nested dicts are merged one level."""
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def rest_framework(**overrides: Any) -> dict[str, Any]:
    """Return ``REST_FRAMEWORK`` with the SDK defaults.

    Dict values (e.g. ``DEFAULT_THROTTLE_RATES``) are merged with the defaults,
    so ``rest_framework(DEFAULT_THROTTLE_RATES={"anon": "50/hour"})`` changes a
    single rate; any other key replaces the default.
    """
    defaults: dict[str, Any] = {
        "DEFAULT_PERMISSION_CLASSES": [
            "rest_framework.permissions.IsAuthenticated",
        ],
        "DEFAULT_AUTHENTICATION_CLASSES": [JWT_AUTHENTICATION],
        "DEFAULT_THROTTLE_CLASSES": [
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.UserRateThrottle",
        ],
        "DEFAULT_THROTTLE_RATES": dict(THROTTLE_RATES),
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
        "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
        "PAGE_SIZE": 20,
    }
    return _merge(defaults, overrides)


def simple_jwt(secret_key: str, **overrides: Any) -> dict[str, Any]:
    """Return ``SIMPLE_JWT``: 30 min access, 12 h rotating refresh + blacklist.

    An empty ``secret_key`` leaves ``SIGNING_KEY`` out, so SimpleJWT signs with
    ``settings.SECRET_KEY``.
    """
    config: dict[str, Any] = {
        "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
        "REFRESH_TOKEN_LIFETIME": timedelta(hours=12),
        "ROTATE_REFRESH_TOKENS": True,
        "BLACKLIST_AFTER_ROTATION": True,
        "UPDATE_LAST_LOGIN": True,
        "ALGORITHM": "HS256",
        "AUTH_HEADER_TYPES": ("Bearer",),
        "USER_ID_FIELD": "id",
        "USER_ID_CLAIM": "user_id",
    }
    if secret_key:
        config["SIGNING_KEY"] = secret_key
    return {**config, **overrides}


def spectacular(title: str, version: str = "0.1.0", **overrides: Any) -> dict:
    """Return ``SPECTACULAR_SETTINGS``; the schema is served to admins only.

    drf-spectacular serves the schema to anyone by default, which would expose
    the whole API surface. Session authentication is accepted so an admin
    logged into the Django admin can open the docs in the browser.
    """
    config: dict[str, Any] = {
        "TITLE": title,
        "VERSION": version,
        "SERVE_INCLUDE_SCHEMA": False,
        "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
        "SERVE_AUTHENTICATION": [
            "rest_framework.authentication.SessionAuthentication",
            JWT_AUTHENTICATION,
        ],
        "COMPONENT_SPLIT_REQUEST": True,
        "SCHEMA_PATH_PREFIX": r"/api/",
    }
    return {**config, **overrides}
