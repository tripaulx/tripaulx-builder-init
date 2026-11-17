"""Runtime configuration a client reads before rendering its auth screens."""

from __future__ import annotations

from django.db import connection
from django_tenants.utils import get_public_schema_name
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from tripaulx.mail.services import email_available
from tripaulx.tenants.conf import app_settings as tenants_settings
from tripaulx.tenants.services.domains import workspace_origin_template

from ...conf import app_settings
from ...services import profiles, registration, verification
from ..schema import untyped
from .base import AccountsAPIView


def _profiles() -> list[dict[str, object]]:
    """Return the registration profiles with the extra fields each one takes."""
    found = []
    for key in profiles.profiles():
        required, optional = profiles.accepted_fields(key)
        found.append({"key": key, "required": required, "optional": optional})
    return found


class AuthConfigView(AccountsAPIView):
    """Feature flags of the account flows and how to reach a workspace."""

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    @untyped
    def get(self, request: Request) -> Response:
        """Return the configuration (nothing secret)."""
        is_public = connection.schema_name == get_public_schema_name()
        return Response(
            {
                "signup_enabled": is_public and bool(app_settings.SIGNUP_ENABLED),
                "registration_enabled": registration.enabled(),
                "registration_profiles": _profiles(),
                "registration_fields": profiles.accepted_fields()[1],
                "email_verification_required": verification.required(),
                "email_available": email_available(),
                "mfa_policy": app_settings.MFA_POLICY,
                "base_domain": tenants_settings.BASE_DOMAIN,
                "workspace_origin_template": workspace_origin_template(request),
            }
        )
