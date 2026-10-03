"""Model used to exercise ``BaseModel``."""

from django.db import models

from tripaulx.core.models import BaseModel


class Note(BaseModel):
    """A note with soft delete."""

    text = models.CharField(max_length=100)
