"""Choices shared by the AI models.

Effort and verbosity values are the literals the providers accept, so the
clients never translate them. The empty value means "inherit from the level
above": skill inherits from agent, agent from the workspace settings, and
empty settings leave the provider default.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Effort(models.TextChoices):
    """How much the model reasons before answering (reasoning models only)."""

    INHERIT = "", _("Inherit")
    MINIMAL = "minimal", _("Minimal")
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")


class Verbosity(models.TextChoices):
    """Answer length asked of the model (OpenAI reasoning models only)."""

    INHERIT = "", _("Inherit")
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")


class AgentRole(models.TextChoices):
    """What the agent does in a run."""

    SPECIALIST = "specialist", _("Specialist")
    COORDINATOR = "coordinator", _("Coordinator")


class EventStatus(models.TextChoices):
    """Outcome of one provider call."""

    SUCCESS = "success", _("Success")
    ERROR = "error", _("Error")


class ExecutionStep(models.TextChoices):
    """Position of a call inside a run."""

    SINGLE = "single", _("Single")
    SPECIALIST = "specialist", _("Specialist")
    CONSOLIDATION = "consolidation", _("Consolidation")


class KeyClosedReason(models.TextChoices):
    """Why a key stopped being the active one."""

    DELETED = "deleted", _("Deleted")
    REPLACED = "replaced", _("Replaced by a new key")
