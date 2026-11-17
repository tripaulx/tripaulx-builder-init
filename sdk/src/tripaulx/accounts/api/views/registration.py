"""Account registration inside the current schema (no invitation)."""

from __future__ import annotations

from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from ...services import login, profiles, registration
from ..serializers import RegistrationSerializer
from .base import AccountsAPIView, session_payload


class RegisterView(AccountsAPIView):
    """Create a member account, then e-mail the verification code.

    The person confirms the code on ``email/verify/``, which logs them in.
    With ``EMAIL_VERIFICATION_REQUIRED`` off, ``session`` already holds the
    tokens and the user.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"
    serializer_class = RegistrationSerializer

    def initial(self, request: Request, *args: object, **kwargs: object) -> None:
        """Only while registration is enabled."""
        if not registration.enabled():
            raise PermissionDenied(_("Registration is disabled."))
        super().initial(request, *args, **kwargs)

    def post(self, request: Request) -> Response:
        """Register."""
        data = self.validated(RegistrationSerializer)
        names = profiles.all_field_names()
        result = registration.register(
            email=data["email"],
            full_name=data["full_name"],
            password=data["password"],
            password_confirm=data["password_confirm"],
            profile=data["profile"],
            extra={name: request.data.get(name) for name in names},
        )
        session = None
        if not result.email_verification_required:
            outcome = login.complete_login(result.user, request, "registration")
            session = session_payload(outcome)
        return Response(
            {
                "email": result.user.email,
                "profile": result.profile,
                "email_verification_required": result.email_verification_required,
                "session": session,
            },
            status=status.HTTP_201_CREATED,
        )
