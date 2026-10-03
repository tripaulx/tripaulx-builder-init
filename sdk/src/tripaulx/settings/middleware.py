"""Default middleware pipeline for multi-tenant projects."""

from __future__ import annotations

SDK_MIDDLEWARE: tuple[str, ...] = (
    # Resolves the tenant from the Host header; must run first.
    "tripaulx.core.middleware.TenantMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)


def middleware(*extra: str, after_security: tuple[str, ...] = ()) -> list[str]:
    """Return the SDK middleware list.

    Args:
        extra: middleware appended at the end of the pipeline.
        after_security: middleware inserted right after ``SecurityMiddleware``
            (e.g. WhiteNoise or CORS, which must run early).
    """
    pipeline = list(SDK_MIDDLEWARE)
    position = pipeline.index("django.middleware.security.SecurityMiddleware") + 1
    pipeline[position:position] = after_security
    return [*pipeline, *extra]
