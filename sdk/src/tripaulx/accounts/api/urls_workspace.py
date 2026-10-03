"""Workspace administration routes, mounted under ``api/workspace/``.

Only on the tenant URLconf; every route requires an owner or admin.
"""

from django.urls import path

from . import views

app_name = "tpsdk_workspace"

urlpatterns = [
    path("members/", views.MemberListView.as_view(), name="member-list"),
    # ``str``: the primary key type belongs to the project's user model.
    path("members/<str:pk>/", views.MemberDetailView.as_view(), name="member-detail"),
    path("invitations/", views.InvitationListView.as_view(), name="invitation-list"),
    path(
        "invitations/<uuid:pk>/",
        views.InvitationDetailView.as_view(),
        name="invitation-detail",
    ),
]
