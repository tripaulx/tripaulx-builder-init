"""Invitations: create, list, revoke and accept (single-use token).

The raw token only travels in the e-mailed link; the database keeps its
sha256. Accepting creates the user with a verified e-mail (the link proved
access to the inbox) and the invited role.
"""

from __future__ import annotations

from datetime import timedelta
import hashlib
import secrets
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext as _

from ..conf import app_settings
from ..models import Invitation, Role
from . import notifications, passwords
from .errors import MembershipError, MembershipForbidden, NotFound


def hash_token(token: str) -> str:
    """Return the sha256 (hex) of a raw invitation token."""
    return hashlib.sha256((token or "").encode()).hexdigest()


def _is_member(email: str) -> bool:
    """Whether a user with ``email`` already exists in this workspace."""
    return get_user_model().objects.filter(email__iexact=email).exists()


def pending() -> QuerySet[Invitation]:
    """Invitations not accepted nor revoked (expired ones included)."""
    return Invitation.objects.filter(accepted_at__isnull=True)


def create(
    actor: Any, email: str, role: str, *, origin: str, workspace: str
) -> Invitation:
    """Invite ``email`` with ``role`` and e-mail the acceptance link.

    A new invitation replaces the pending ones of the same address.
    """
    email = get_user_model().objects.normalize_email(email).lower()
    if role not in Role.values:
        raise MembershipError(_("Unknown role."))
    if role == Role.OWNER and actor.role != Role.OWNER:
        raise MembershipForbidden(_("Only an owner can grant the owner role."))
    if _is_member(email):
        raise MembershipError(_("This person is already a member."))
    for previous in pending().filter(email__iexact=email):
        previous.delete()
    token = secrets.token_urlsafe(32)
    ttl = int(app_settings.INVITATION_TTL_SECONDS)
    invitation = Invitation.objects.create(
        email=email,
        role=role,
        token_hash=hash_token(token),
        invited_by=actor,
        expires_at=timezone.now() + timedelta(seconds=ttl),
    )
    url = app_settings.INVITATION_ACCEPT_URL.format(origin=origin, token=token)
    notifications.send_invitation(
        email, url=url, inviter=actor, workspace=workspace, days=max(1, ttl // 86400)
    )
    return invitation


def revoke(pk: Any) -> None:
    """Revoke a pending invitation (soft delete)."""
    invitation = pending().filter(pk=pk).first()
    if invitation is None:
        raise NotFound(_("Invitation not found."))
    invitation.delete()


def accept(token: str, password: str, **profile: str) -> Any:
    """Create the invited user; ``profile`` may hold first and last name."""
    invitation = Invitation.objects.filter(token_hash=hash_token(token)).first()
    if invitation is None or not invitation.is_pending:
        raise MembershipError(_("This invitation is invalid or has expired."))
    if _is_member(invitation.email):
        raise MembershipError(_("This person is already a member."))
    passwords.check_strength(password)
    with transaction.atomic():
        claimed = Invitation.objects.filter(
            pk=invitation.pk, accepted_at__isnull=True
        ).update(accepted_at=timezone.now())
        if not claimed:
            raise MembershipError(_("This invitation is invalid or has expired."))
        return get_user_model().objects.create_user(
            email=invitation.email,
            password=password,
            role=invitation.role,
            email_verified=True,
            first_name=(profile.get("first_name") or "")[:150],
            last_name=(profile.get("last_name") or "")[:150],
        )
