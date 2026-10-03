"""Parameter precedence (skill > agent > settings), skills and the team brief."""

from __future__ import annotations

from typing import Any

from tripaulx.ai.catalog import services as catalog
from tripaulx.ai.conf import app_settings
from tripaulx.ai.providers import AIError
from tripaulx.ai.providers.errors import make

from .results import Params, StepResult


def first_set(*values: Any) -> Any:
    """Return the first value that is neither ``None`` nor empty."""
    for value in values:
        if value is not None and value != "":
            return value
    return None


def skills_of(agent: Any) -> list[tuple[Any, Any]] | AIError:
    """``[(AgentSkill, SkillVersion)]`` of the live skills, published only.

    A required skill without a version is an error; an optional one is
    skipped.
    """
    items = []
    for link in agent.live_skills():
        version = link.skill.published_version
        if version is None:
            if link.required:
                return make("skill_not_published", name=link.skill.name)
            continue
        items.append((link, version))
    return items


def resolve(
    settings: Any, agent: Any, skills: list[tuple[Any, Any]]
) -> Params | AIError:
    """Resolve each parameter, field by field, from what is set.

    Among skills, the first one (in order) that sets a field wins. The model
    must be an active catalog model of the configured provider.
    """
    skill_rows = [link.skill for link, _version in skills]
    identifier = first_set(
        *(s.model_identifier for s in skill_rows),
        agent.model_identifier,
        settings.model_identifier,
    )
    model = catalog.find_active(settings.provider, identifier or "")
    if model is None:
        return make("no_model")
    return Params(
        model=model,
        effort=first_set(*(s.effort for s in skill_rows), agent.effort, settings.effort)
        or "",
        verbosity=agent.verbosity or "",
        max_output_tokens=first_set(
            *(s.max_output_tokens for s in skill_rows),
            agent.max_output_tokens,
            settings.max_output_tokens,
        ),
        temperature=agent.temperature,
    )


def brief(steps: list[StepResult]) -> str:
    """Output of the specialists that ran, oldest first, cut from the start."""
    limit = int(app_settings.AI_BRIEF_LIMIT_CHARS)
    blocks = [
        f"### {s.agent.name}\n{s.text.strip()}"
        for s in steps
        if s.ok and s.text.strip()
    ]
    text = "\n\n".join(blocks)
    if len(text) > limit:
        # Keep the END (the latest material whole) and flag the cut.
        text = "[…earlier material cut…]\n" + text[-limit:]
    return text


def skills_for_event(skills: list[tuple[Any, Any]]) -> list[dict[str, Any]]:
    """Return the skill snapshot stored on the event."""
    return [
        {
            "id": str(link.skill_id),
            "slug": link.skill.slug,
            "name": link.skill.name,
            "version": version.number,
        }
        for link, version in skills
    ]
