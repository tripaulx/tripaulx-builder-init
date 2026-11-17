"""Workspace lookup by slug, for "which workspace?" and signup screens."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError

from ..models import Workspace
from ..validators.slug import validate_workspace_slug


@dataclass(frozen=True)
class SlugStatus:
    """What a slug is: an existing workspace, free to take, or unusable."""

    slug: str
    exists: bool
    available: bool
    name: str = ""
    reason: str = ""


def slug_status(slug: str) -> SlugStatus:
    """Describe ``slug``; the answer is only valid at call time.

    An inactive workspace neither exists (nobody logs into it) nor is
    available (its address is not free).
    """
    try:
        validate_workspace_slug(slug)
    except ValidationError as exc:
        return SlugStatus(slug, exists=False, available=False, reason=exc.messages[0])
    workspace = Workspace.objects.filter(schema_name=slug).first()
    if workspace is None:
        return SlugStatus(slug, exists=False, available=True)
    if not workspace.is_active:
        return SlugStatus(slug, exists=False, available=False)
    return SlugStatus(slug, exists=True, available=False, name=workspace.name)
