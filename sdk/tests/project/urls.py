"""Tenant URLconf of the SDK test project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("tripaulx.accounts.api.urls")),
    path("api/workspace/", include("tripaulx.accounts.api.urls_workspace")),
    path("api/v1/ai/", include("tripaulx.ai.api.urls")),
    path("", include("tripaulx.core.urls")),
]
