"""Public-schema routes under ``api/auth/``: workspace signup and lookup.

Mount it next to :mod:`tripaulx.accounts.api.urls` in the public URLconf::

    path("api/auth/", include("tripaulx.accounts.api.urls_public")),
    path("api/auth/", include("tripaulx.accounts.api.urls")),
"""

from django.urls import path

from . import views

app_name = "tpsdk_accounts_public"

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path(
        "workspaces/<str:slug>/",
        views.WorkspaceLookupView.as_view(),
        name="workspace-lookup",
    ),
]
