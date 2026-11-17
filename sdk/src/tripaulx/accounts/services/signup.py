"""Signup: a new owner creates a new workspace (public schema).

Steps: validate the input, provision the workspace (row + schema + domain),
create the owner inside the new schema with an unverified e-mail, and send
the verification code. The owner then verifies the e-mail and logs in on the
workspace domain. With ``EMAIL_VERIFICATION_REQUIRED`` off, the owner starts
verified and no code is sent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from tripaulx.tenants.models import Workspace
from tripaulx.tenants.services.domains import workspace_domain
from tripaulx.tenants.services.provisioning import provision_workspace
from tripaulx.tenants.services.slugs import normalize_slug

from ..models import EmailCodePurpose, Role
from ..signals import user_signed_up
from . import email_codes, identity, verification
from .errors import SignupError


@dataclass(frozen=True)
class SignupResult:
    """What signup created."""

    workspace: Workspace
    owner: Any
    domain: str


def _clean_workspace(name: str, slug: str) -> str:
    """Validate the workspace name; return the slug to use."""
    name = (name or "").strip()
    if not name:
        raise SignupError(_("Enter the workspace name."), field="workspace_name")
    return (slug or normalize_slug(name)).strip()


def signup(
    *,
    email: str,
    full_name: str,
    password: str,
    password_confirm: str,
    workspace_name: str,
    slug: str = "",
) -> SignupResult:
    """Create the workspace and its owner; send the verification code if due."""
    owner_input = identity.clean_person(email, full_name, password, password_confirm)
    slug = _clean_workspace(workspace_name, slug)
    must_verify = verification.required()

    def create_owner(workspace: Workspace) -> Any:
        owner = get_user_model().objects.create_user(
            email=owner_input.email,
            password=password,
            first_name=owner_input.first_name,
            last_name=owner_input.last_name,
            role=Role.OWNER,
            email_verified=not must_verify,
        )
        if must_verify:
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
