"""Workspace signup (public schema only)."""

from __future__ import annotations

from django.db import connection
from django.http import Http404
from django.http.request import split_domain_port
from django.utils.translation import gettext as _
from django_tenants.utils import get_public_schema_name
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from ...conf import app_settings
from ...services import signup
from ..serializers import SignupSerializer
from .base import AccountsAPIView


class SignupView(AccountsAPIView):
    """Create a workspace and its owner, then e-mail the verification code.

    The owner verifies the e-mail and logs in on ``workspace_url``.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"
    serializer_class = SignupSerializer

    def initial(self, request: Request, *args: object, **kwargs: object) -> None:
        """Only on the public schema, and only while signup is enabled."""
        if connection.schema_name != get_public_schema_name():
            raise Http404
        if not app_settings.SIGNUP_ENABLED:
            raise PermissionDenied(_("Signup is disabled."))
        super().initial(request, *args, **kwargs)

    def post(self, request: Request) -> Response:
        """Sign up."""
        data = self.validated(SignupSerializer)
        result = signup.signup(
            email=data["email"],
            password=data["password"],
            workspace_name=data["workspace_name"],
            slug=data["slug"],
        )
        _host, port = split_domain_port(request.get_host())
        authority = f"{result.domain}:{port}" if port else result.domain
        return Response(
            {
                "workspace_slug": result.workspace.schema_name,
                "workspace_domain": result.domain,
                "workspace_url": f"{request.scheme}://{authority}",
                "email": result.owner.email,
                "email_verification_required": True,
            },
            status=status.HTTP_201_CREATED,
        )
