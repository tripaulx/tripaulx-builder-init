"""URLconf of workspace (tenant) schemas."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(f"{settings.ADMIN_URL_PREFIX}/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("tripaulx.core.urls")),
]
