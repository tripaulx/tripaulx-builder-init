"""Middleware pipeline: SDK tenant resolution first, WhiteNoise early."""

from tripaulx.settings.middleware import middleware

MIDDLEWARE = middleware(after_security=("whitenoise.middleware.WhiteNoiseMiddleware",))
