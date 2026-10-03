"""URLconf of the public schema (apex domain: platform admin, signup)."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path(f"{settings.ADMIN_URL_PREFIX}/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    # Signup (creates a workspace) exists only here.
    path("api/auth/", include("tripaulx.accounts.api.urls_public")),
    path("api/auth/", include("tripaulx.accounts.api.urls")),
    # Terms of use and privacy policy, also served on the apex domain.
    path("api/legal/public/", include("tripaulx.legal.api.urls_public")),
    # OpenAPI docs, served to platform admins only (SPECTACULAR_SETTINGS).
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    path("", include("tripaulx.core.urls")),
]
