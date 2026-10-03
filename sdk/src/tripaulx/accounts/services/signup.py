"""Signup: a new owner creates a new workspace (public schema).

Steps: validate the input, provision the workspace (row + schema + domain),
create the owner inside the new schema with an unverified e-mail, and send
the verification code. The owner then verifies the e-mail and logs in on the
workspace domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext as _

from tripaulx.tenants.models import Workspace
from tripaulx.tenants.services.domains import workspace_domain
from tripaulx.tenants.services.provisioning import provision_workspace
from tripaulx.tenants.services.slugs import normalize_slug

from ..models import EmailCodePurpose, Role
from ..signals import user_signed_up
from . import email_codes, passwords
from .errors import PasswordError, SignupError


@dataclass(frozen=True)
class SignupResult:
    """What signup created."""

    workspace: Workspace
    owner: Any
    domain: str


def _clean(email: str, password: str, name: str, slug: str) -> tuple[str, str]:
    """Validate the input; return the normalized e-mail and slug."""
    name = (name or "").strip()
    if not name:
        raise SignupError(_("Enter the workspace name."), field="workspace_name")
    try:
        validate_email(email)
    except ValidationError as exc:
        raise SignupError(_("Enter a valid e-mail address."), field="email") from exc
    try:
        passwords.check_strength(password)
    except PasswordError as exc:
        raise SignupError(exc.message, field="password") from exc
    email = get_user_model().objects.normalize_email(email)
    return email, (slug or normalize_slug(name)).strip()


def signup(
    *, email: str, password: str, workspace_name: str, slug: str = ""
) -> SignupResult:
    """Create the workspace and its owner; send the verification code."""
    email, slug = _clean(email, password, workspace_name, slug)

    def create_owner(workspace: Workspace) -> Any:
        owner = get_user_model().objects.create_user(
            email=email, password=password, role=Role.OWNER, email_verified=False
        )
        email_codes.issue_code(owner, EmailCodePurpose.EMAIL_VERIFY)
        return owner

    try:
        workspace, owner = provision_workspace(
            workspace_name.strip(), slug, setup=create_owner
        )
    except ValidationError as exc:
        raise SignupError(" ".join(exc.messages), field="slug") from exc
    user_signed_up.send(sender=type(owner), user=owner, workspace=workspace)
    return SignupResult(workspace=workspace, owner=owner, domain=workspace_domain(slug))
