"""Turn free text into a workspace slug and check whether it is free."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils.text import slugify

from ..models import Workspace
from ..validators.slug import validate_workspace_slug

MAX_LENGTH = 30


def normalize_slug(text: str) -> str:
    """Return a slug candidate for ``text`` (it may still be invalid).

    Accents are stripped, separators become ``_`` and a leading digit gets a
    ``w`` prefix so the result can match the slug pattern.
    """
    slug = slugify(text or "").replace("-", "_").strip("_")
    if slug and slug[0].isdigit():
        slug = f"w{slug}"
    return slug[:MAX_LENGTH].rstrip("_")


def is_slug_available(slug: str) -> bool:
    """Whether ``slug`` is valid, not reserved and not taken by a workspace.

    The answer is only valid at call time; workspace creation must check again
    inside its own transaction.
    """
    try:
        validate_workspace_slug(slug)
    except ValidationError:
        return False
    return not Workspace.objects.filter(schema_name=slug).exists()
