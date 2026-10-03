"""Operations on skills the table cannot do alone: publish and duplicate."""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Max
from django.utils.translation import gettext as _

from tripaulx.ai.models import Skill, SkillVersion

from .keys import actor_label


class NothingToPublish(ValueError):
    """The draft equals the published version (or is empty)."""


def publish(skill: Skill, *, by: Any, note: str = "") -> SkillVersion:
    """Freeze the draft as the next version and make it the one in force.

    ``select_for_update`` on the skill: two simultaneous publications cannot
    race for the same number (the constraint would refuse the second one
    with a 500).
    """
    with transaction.atomic():
        locked = Skill.all_objects.select_for_update().get(pk=skill.pk)
        instructions = locked.instructions.strip()
        if not instructions:
            raise NothingToPublish(_("Write the instructions before publishing."))
        current = locked.published_version
        if current is not None and current.instructions.strip() == instructions:
            raise NothingToPublish(
                _("Nothing to publish: the draft equals the published version.")
            )
        last = locked.versions.aggregate(n=Max("number"))["n"] or 0
        version = SkillVersion.objects.create(
            skill=locked,
            number=last + 1,
            instructions=instructions,
            note=(note or "").strip()[:200],
            published_by=by if getattr(by, "pk", None) else None,
            published_by_label=actor_label(by),
        )
        locked.published_version = version
        locked.save(update_fields=["published_version", "updated_at"])
        skill.published_version = version
        return version


def copy_name(name: str) -> str:
    """Return the name of a copy, unique among live skills."""
    base = _("%(name)s (copy)") % {"name": name}
    candidate, counter = base[:80], 2
    while Skill.objects.filter(name__iexact=candidate).exists():
        candidate = f"{base} {counter}"[:80]
        counter += 1
    return candidate


def duplicate(skill: Skill, *, by: Any) -> Skill:
    """Copy draft and parameters into a new skill without a published version."""
    return Skill.objects.create(
        name=copy_name(skill.name),
        description=skill.description,
        instructions=skill.instructions,
        model_identifier=skill.model_identifier,
        effort=skill.effort,
        max_output_tokens=skill.max_output_tokens,
        active=skill.active,
        order=skill.order,
        created_by=by if getattr(by, "pk", None) else None,
    )
