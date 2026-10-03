"""Public-schema URLconf of the SDK test project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("tripaulx.accounts.api.urls_public")),
    path("api/auth/", include("tripaulx.accounts.api.urls")),
    path("", include("tripaulx.core.urls")),
]
