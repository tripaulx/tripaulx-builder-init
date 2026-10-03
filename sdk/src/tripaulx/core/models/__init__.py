"""Abstract models and managers reused by SDK apps and projects."""

from .base import BaseModel
from .managers import AliveManager

__all__ = ["AliveManager", "BaseModel"]
