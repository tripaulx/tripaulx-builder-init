"""Validation helpers shared by the agent, skill and settings serializers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.utils.translation import gettext as _
from rest_framework import serializers

from tripaulx.ai.services import model_choice
from tripaulx.ai.services.keys import actor_label


def unique_name(model: type[models.Model], name: str, instance: Any) -> str:
    """Require a name unique among live rows (a 400, not an IntegrityError)."""
    cleaned = (name or "").strip()
    if not cleaned:
        raise serializers.ValidationError(_("Enter the name."))
    taken = model.objects.filter(name__iexact=cleaned)
    if instance is not None:
        taken = taken.exclude(pk=instance.pk)
    if taken.exists():
        raise serializers.ValidationError(
            _("“%(name)s” already exists.") % {"name": cleaned}
        )
    return cleaned


def checked_model(identifier: str, provider: str | None = None) -> str:
    """Return the model identifier if it may be chosen (``model_choice``)."""
    try:
        return model_choice.check(identifier, provider)
    except model_choice.InvalidModelChoice as exc:
        raise serializers.ValidationError(str(exc)) from exc


def django_rule(rule: Callable[[Any], Any], value: Any) -> Any:
    """Run a Django validator and re-raise its error for DRF."""
    try:
        return rule(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages) from exc


def user_label(user: Any) -> str:
    """Display name of a user (empty without one)."""
    return actor_label(user)


def require_text(value: str, message: str) -> str:
    """Refuse blank text with ``message``."""
    if not (value or "").strip():
        raise serializers.ValidationError(message)
    return value
