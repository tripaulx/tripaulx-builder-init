"""Prompt assembly: system layers and the input template.

The system prompt is built in LAYERS, each with its own owner and life cycle,
always in this order and with delimited headers:

1. base       - ``TRIPAULX["AI_BASE_PROMPT"]``, the product (per project).
2. agent      - identity and rules (edited by the workspace).
3. skills     - the PUBLISHED version of each one, in attached order.
4. overlay    - what the caller injects for this call only.
5. format     - the JSON Schema, when the agent requires structured output.

The user message comes from the agent's ``input_template``, rendered with
``format_map`` and a dict that leaves unknown placeholders as literal text: a
mistyped ``{foo}`` does not break the run. ONLY THE TEMPLATE goes through
``format``; the input enters as a VALUE, so braces inside it are not read.
"""

from __future__ import annotations

from collections.abc import Sequence
import json
from typing import Any

from django.utils.translation import gettext as _

from tripaulx.ai.conf import app_settings

BRIEF_HEADER = "--- MATERIAL ALREADY PRODUCED IN THIS RUN ---"


class _SafeDict(dict):
    """``format_map`` dict that keeps unknown placeholders as text."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _section(title: str, body: str) -> str:
    return f"--- {title} ---\n{body.strip()}\n---"


def base_prompt() -> str:
    """Return the configured base prompt (may be empty)."""
    return (app_settings.AI_BASE_PROMPT or "").strip()


def build_instructions(
    agent: Any,
    versions: Sequence[Any],
    *,
    overlay: str = "",
    output_schema: dict | None = None,
) -> str:
    """Build the system prompt in five layers (empty layers are skipped).

    ``versions`` are :class:`SkillVersion` rows (the published one of each
    skill), already filtered and ordered by the caller.
    """
    parts = [base_prompt()] if base_prompt() else []
    if agent.instructions and agent.instructions.strip():
        parts.append(_section("AGENT IDENTITY AND RULES", agent.instructions))
    for version in versions:
        title = f"SKILL: {version.skill.name} (v{version.number})"
        parts.append(_section(title, version.instructions))
    if overlay and overlay.strip():
        parts.append(_section("CONTEXT OF THIS CALL", overlay))
    if output_schema:
        body = json.dumps(output_schema, ensure_ascii=False, indent=2)
        body += "\nAnswer only with the JSON, with no text outside it."
        parts.append(_section("OUTPUT FORMAT", body))
    return "\n\n".join(parts)


def build_input(agent: Any, text: str, *, context: str = "", brief: str = "") -> str:
    """Build the user message: rendered template plus the team brief."""
    message = render_template(agent.input_template, input=text, context=context)
    if brief and brief.strip():
        message = f"{message}\n\n{BRIEF_HEADER}\n{brief.strip()}"
    return message


def render_template(template: str, **values: str) -> str:
    """Apply a tolerant ``format_map``; return the raw template if invalid."""
    try:
        return (template or "{input}").format_map(_SafeDict(**values))
    except (ValueError, IndexError, AttributeError):
        return template


def template_complaint(template: str) -> str | None:
    """Why the input template is unusable, or ``None``.

    ``{input}`` is required (without it the material never reaches the
    model), and what ``format`` refuses is refused here, close to whoever
    typed it, instead of failing at run time.
    """
    text = template or ""
    if "{input}" not in text:
        return _("The template must contain {input}.")
    try:
        text.format_map(_SafeDict(input="", context=""))
    except (ValueError, IndexError, AttributeError) as exc:
        return _(
            "Invalid template: %(error)s. For a literal brace, double it: {{ }}."
        ) % {"error": exc}
    return None
