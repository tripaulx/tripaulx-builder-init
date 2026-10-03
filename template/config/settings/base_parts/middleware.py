"""Middleware pipeline: SDK tenant resolution first, WhiteNoise and CORS early."""

from tripaulx.settings.middleware import middleware

MIDDLEWARE = middleware(
    after_security=(
        "whitenoise.middleware.WhiteNoiseMiddleware",
        "corsheaders.middleware.CorsMiddleware",
    )
)
