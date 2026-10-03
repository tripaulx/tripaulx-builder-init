"""Abstract base model: UUID primary key, audit timestamps and soft delete."""

from __future__ import annotations

from typing import Any
import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import AliveManager


class BaseModel(models.Model):
    """Abstract base for SDK and project models."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)
    deleted_at = models.DateTimeField(
        _("deleted at"), null=True, blank=True, db_index=True
    )

    objects = AliveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"

    @property
    def is_deleted(self) -> bool:
        """Whether the row is soft-deleted."""
        return self.deleted_at is not None

    def delete(
        self, using: Any = None, keep_parents: bool = False, hard: bool = False
    ) -> tuple[int, dict[str, int]]:
        """Soft delete by default; ``hard=True`` removes the row for real.

        The change reason is picked up by django-simple-history when the
        project tracks the model.
        """
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.deleted_at = timezone.now()
        self._change_reason = "Soft delete"
        self.save(update_fields=["deleted_at", "updated_at"])
        return (0, {})

    def restore(self) -> None:
        """Undo a soft delete."""
        self.deleted_at = None
        self._change_reason = "Restore after soft delete"
        self.save(update_fields=["deleted_at", "updated_at"])
