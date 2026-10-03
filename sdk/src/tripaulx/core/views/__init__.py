"""Views served by the core app."""

from .health import healthz, readyz

__all__ = ["healthz", "readyz"]
