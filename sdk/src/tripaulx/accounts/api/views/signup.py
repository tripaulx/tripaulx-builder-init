"""Workspace signup (public schema only)."""

from __future__ import annotations

from django.db import connection
from django.http import Http404
from django.utils.translation import gettext as _
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from tripaulx.tenants.services.domains import workspace_origin

from ...conf import app_settings
from ...services import login, signup, verification
from ..serializers import SignupSerializer
from .base import AccountsAPIView, session_payload


class SignupView(AccountsAPIView):
    """Create a workspace and its owner, then e-mail the verification code.

    The owner verifies the e-mail and logs in on ``workspace_url``. With
    ``EMAIL_VERIFICATION_REQUIRED`` off, ``session`` already holds the owner's
    tokens (bound to the new workspace) and user.
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
            full_name=data["full_name"],
            password=data["password"],
            password_confirm=data["password_confirm"],
            workspace_name=data["workspace_name"],
            slug=data["slug"],
        )
        slug = result.workspace.schema_name
        origin = workspace_origin(request, slug)
        session = None
        if not verification.required():
            # Inside the new schema, so the tokens carry its schema claim.
            with schema_context(slug):
                outcome = login.complete_login(result.owner, request, "signup")
                session = session_payload(outcome)
        return Response(
            {
                "workspace_slug": slug,
                "workspace_name": result.workspace.name,
                "workspace_domain": result.domain,
                "workspace_url": origin,
                "api_url": f"{origin}/api",
                "email": result.owner.email,
                "email_verification_required": session is None,
                "session": session,
            },
            status=status.HTTP_201_CREATED,
        )
