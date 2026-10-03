"""Public legal documents (terms of use, privacy policy), no authentication.

Mount it on both URLconfs, apex domain and workspaces::

    path("api/legal/public/", include("tripaulx.legal.api.urls_public")),
"""

from django.urls import path

from . import views

app_name = "tpsdk_legal_public"

urlpatterns = [
    path("", views.PublicLegalDocumentListView.as_view(), name="document-list"),
    path(
        "<slug:slug>/",
        views.PublicLegalDocumentDetailView.as_view(),
        name="document-detail",
    ),
]
