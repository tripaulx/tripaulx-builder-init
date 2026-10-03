"""URLconf of workspace (tenant) schemas."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path(f"{settings.ADMIN_URL_PREFIX}/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("api/auth/", include("tripaulx.accounts.api.urls")),
    path("api/workspace/", include("tripaulx.accounts.api.urls_workspace")),
    # Legal: governance documents (restricted) and terms/privacy (public).
    path("api/v1/legal/", include("tripaulx.legal.api.urls")),
    path("api/legal/public/", include("tripaulx.legal.api.urls_public")),
    path("api/v1/ai/", include("tripaulx.ai.api.urls")),
    path("", include("tripaulx.core.urls")),
]

# OpenAPI docs on workspaces only in development (always admin-only).
if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="api-schema"),
            name="api-docs",
        ),
    ]
