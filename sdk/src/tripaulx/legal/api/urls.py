"""Restricted legal area (every document, authorized users only).

Mount it on the tenant URLconf only::

    path("api/v1/legal/", include("tripaulx.legal.api.urls")),
"""

from django.urls import path

from . import views

app_name = "tpsdk_legal"

urlpatterns = [
    path("", views.LegalDocumentListView.as_view(), name="document-list"),
    path(
        "<slug:slug>/", views.LegalDocumentDetailView.as_view(), name="document-detail"
    ),
]
