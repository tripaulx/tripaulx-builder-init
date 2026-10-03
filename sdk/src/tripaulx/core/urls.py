"""URL routes of the core app (probes are also answered by the middleware)."""

from django.urls import path

from .views import healthz, readyz

app_name = "tpsdk_core"

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("readyz/", readyz, name="readyz"),
]
