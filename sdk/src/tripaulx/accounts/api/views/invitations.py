"""Invitations: admins create, list and revoke; the invitee accepts."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from ...services import invitations, login
from ..permissions import IsWorkspaceAdmin
from ..schema import untyped
from ..serializers import (
    InvitationAcceptSerializer,
    InvitationCreateSerializer,
    InvitationSerializer,
)
from .base import AccountsAPIView, AccountsListAPIView, login_response


class InvitationListView(AccountsListAPIView):
    """List pending invitations (GET) or invite someone (POST)."""

    permission_classes = [IsWorkspaceAdmin]
    serializer_class = InvitationSerializer

    def get_queryset(self) -> QuerySet:
        """Invitations not accepted nor revoked."""
        return invitations.pending().select_related("invited_by")

    def post(self, request: Request) -> Response:
        """Create the invitation and e-mail a link built from this host."""
        data = self.validated(InvitationCreateSerializer)
        tenant = getattr(request, "tenant", None)
        invitation = invitations.create(
            request.user,
            data["email"],
            data["role"],
            origin=f"{request.scheme}://{request.get_host()}",
            workspace=getattr(tenant, "name", ""),
        )
        return Response(
            InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED
        )


class InvitationDetailView(AccountsAPIView):
    """Revoke a pending invitation."""

    permission_classes = [IsWorkspaceAdmin]

    @untyped
    def delete(self, request: Request, pk: Any) -> Response:
        """Revoke it; the link stops working."""
        invitations.revoke(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvitationAcceptView(AccountsAPIView):
    """Accept an invitation: create the account and log in."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"
    serializer_class = InvitationAcceptSerializer

    def post(self, request: Request) -> Response:
        """Create the user (verified e-mail, invited role) and return tokens."""
        data = self.validated(InvitationAcceptSerializer)
        user = invitations.accept(
            data["token"],
            data["password"],
            data["password_confirm"],
            full_name=data["full_name"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )
        outcome = login.complete_login(user, request, "invitation")
        response = login_response(outcome)
        response.status_code = status.HTTP_201_CREATED
        return response
