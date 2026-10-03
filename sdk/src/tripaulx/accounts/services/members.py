"""Workspace members: list, change role and deactivate.

Rules:

- Only an owner can change an owner, or grant the owner role.
- The workspace always keeps at least one active owner.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils.translation import gettext as _

from ..models import Role
from . import passwords
from .errors import MembershipError, MembershipForbidden, NotFound


def members() -> QuerySet:
    """Every user of the workspace (active or not), ordered by e-mail."""
    return get_user_model().objects.order_by("email")


def get_member(pk: Any) -> Any:
    """Return the member ``pk`` or raise :class:`NotFound`."""
    try:
        member = members().filter(pk=pk).first()
    except (ValueError, ValidationError):
        member = None
    if member is None:
        raise NotFound(_("Member not found."))
    return member


def _check_owner_rules(actor: Any, member: Any, new_role: str | None) -> None:
    """Refuse what only an owner may do."""
    if actor.role == Role.OWNER:
        return
    if member.role == Role.OWNER:
        raise MembershipForbidden(_("Only an owner can change another owner."))
    if new_role == Role.OWNER:
        raise MembershipForbidden(_("Only an owner can grant the owner role."))


def _ensure_another_owner(member: Any) -> None:
    """Refuse removing the last active owner (rows locked against races)."""
    if member.role != Role.OWNER or not member.is_active:
        return
    owners = (
        get_user_model()
        .objects.select_for_update()
        .filter(role=Role.OWNER, is_active=True)
        .exclude(pk=member.pk)
    )
    if not list(owners):
        raise MembershipError(_("The workspace needs at least one owner."))


def change_role(actor: Any, member: Any, role: str) -> Any:
    """Give ``member`` a new role, following the owner rules."""
    if role not in Role.values:
        raise MembershipError(_("Unknown role."))
    _check_owner_rules(actor, member, role)
    with transaction.atomic():
        if role != Role.OWNER:
            _ensure_another_owner(member)
        member.role = role
        member.save(update_fields=["role"])
    return member


def deactivate(actor: Any, member: Any) -> Any:
    """Deactivate ``member`` and end their sessions (the row is kept)."""
    _check_owner_rules(actor, member, None)
    with transaction.atomic():
        _ensure_another_owner(member)
        member.is_active = False
        member.save(update_fields=["is_active"])
    passwords.end_sessions(member)
    return member
