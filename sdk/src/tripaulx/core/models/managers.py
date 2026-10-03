"""Managers supporting soft delete."""

from __future__ import annotations

from django.db import models


class AliveManager(models.Manager):
    """Default manager that hides soft-deleted rows (``deleted_at`` set).

    The plain ``all_objects`` manager still sees every row. ``BaseModel`` sets
    ``base_manager_name = "all_objects"`` so reverse relations, the admin and
    audit history keep reaching soft-deleted rows.
    """

    def get_queryset(self) -> models.QuerySet:
        """Return only rows that were not soft-deleted."""
        return super().get_queryset().filter(deleted_at__isnull=True)
