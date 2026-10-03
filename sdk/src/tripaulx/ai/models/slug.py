"""Unique slugs per table, with a numeric suffix on collision."""

from __future__ import annotations

from django.db import models
from django.utils.text import slugify


def unique_slug(
    instance: models.Model, text: str, *, default: str, length: int = 80
) -> str:
    """Slug of ``text`` that collides with **no** row of the table.

    Soft-deleted rows count on purpose (``all_objects``): the slug is the
    stable name references use, so a deleted and recreated agent becomes
    ``-2`` instead of reusing the slug of a row still in the history.
    """
    base = slugify(text)[:length] or default
    slug = base
    counter = 2
    model = type(instance)
    while model.all_objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        suffix = f"-{counter}"
        slug = f"{base[: length - len(suffix)]}{suffix}"
        counter += 1
    return slug
