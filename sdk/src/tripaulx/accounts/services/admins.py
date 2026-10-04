"""Create a workspace's administrator from the command line (no e-mail loop).

The person running the command proves control of the server, so the e-mail is
marked verified. Validation is the same as signup: full name, e-mail, and a
password checked against Django's validators *with* the person's attributes.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext as _
from django_tenants.utils import schema_context

from tripaulx.tenants.models import Workspace

from ..models import Role
from . import identity
from .errors import AccountsError


class AdminError(AccountsError):
    """The administrator cannot be created with this input."""


def has_owner(schema: str) -> bool:
    """Whether ``schema`` exists and already has an active owner."""
    if not Workspace.objects.filter(schema_name=schema).exists():
        return False
    with schema_context(schema):
        return get_user_model().objects.filter(role=Role.OWNER, is_active=True).exists()


def check_identity(schema: str, email: str, full_name: str) -> tuple[str, str, str]:
    """Validate workspace, e-mail and name; return ``(email, first, last)``."""
    if not Workspace.objects.filter(schema_name=schema).exists():
        raise AdminError(_("Workspace %(schema)s does not exist.") % {"schema": schema})
    try:
        validate_email(email)
    except ValidationError as exc:
        raise AdminError(_("Enter a valid e-mail address."), field="email") from exc
    first, last = identity.split_full_name(full_name)
    if not first:
        raise AdminError(_("Enter your full name."), field="full_name")
    email = get_user_model().objects.normalize_email(email)
    with schema_context(schema):
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise AdminError(
                _("A user with this e-mail already exists in this workspace."),
                field="email",
            )
    return email, first, last


def create_admin(
    schema: str,
    email: str,
    full_name: str,
    password: str,
    confirmation: str,
    *,
    role: str = Role.OWNER,
    superuser: bool = True,
) -> Any:
    """Create the user inside ``schema``; raise ``AccountsError`` on bad input."""
    email, first, last = check_identity(schema, email, full_name)
    identity.check_new_password(
        password, confirmation, identity.candidate_user(email, first, last)
    )
    with schema_context(schema):
        return get_user_model().objects.create_user(
            email=email,
            password=password,
            first_name=first,
            last_name=last,
            role=role,
            email_verified=True,
            is_staff=superuser,
            is_superuser=superuser,
        )
