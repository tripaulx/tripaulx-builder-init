"""Workspace members (admins only): list, change role, (re)activate."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from ...services import members
from ..permissions import IsWorkspaceAdmin
from ..serializers import MemberRoleSerializer, MemberSerializer
from .base import AccountsAPIView, AccountsListAPIView


class MemberListView(AccountsListAPIView):
    """Every member of the workspace, paginated."""

    permission_classes = [IsWorkspaceAdmin]
    serializer_class = MemberSerializer

    def get_queryset(self) -> QuerySet:
        """All users of this schema."""
        return members.members()


class MemberDetailView(AccountsAPIView):
    """Read (GET), change the role of (PATCH) or deactivate (DELETE) a member."""

    permission_classes = [IsWorkspaceAdmin]
    serializer_class = MemberRoleSerializer

    def get(self, request: Request, pk: Any) -> Response:
        """Return the member."""
        return Response(MemberSerializer(members.get_member(pk)).data)

    def patch(self, request: Request, pk: Any) -> Response:
        """Change the role (owners can only be changed by owners)."""
        role = self.validated(MemberRoleSerializer)["role"]
        member = members.change_role(request.user, members.get_member(pk), role)
        return Response(MemberSerializer(member).data)

    def delete(self, request: Request, pk: Any) -> Response:
        """Deactivate the member and end their sessions."""
        members.deactivate(request.user, members.get_member(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MemberReactivateView(AccountsAPIView):
    """Give a deactivated member access again (POST)."""

    permission_classes = [IsWorkspaceAdmin]

    @extend_schema(request=None, responses=MemberSerializer)
    def post(self, request: Request, pk: Any) -> Response:
        """Reactivate the member and return it."""
        member = members.reactivate(request.user, members.get_member(pk))
        return Response(MemberSerializer(member).data)
