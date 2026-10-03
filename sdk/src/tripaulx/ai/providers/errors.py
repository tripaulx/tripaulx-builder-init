"""The single AI error taxonomy: stable codes plus translated sentences.

Every path that can go wrong (before reaching the provider: AI disabled, no
key, cap; at the provider: key rejected, limits, outage; after it: cut
answer, invalid JSON) becomes an :class:`AIError` with a ``code`` clients and
the report recognize, a ``message`` users read and a technical ``detail``.
Codes, not text: never match substrings of a provider message.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class AIError:
    """A typed error: stable code, translated sentence, technical detail."""

    code: str
    message: str
    http_status: int | None = None
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return the error as a JSON-ready dict."""
        return {
            "code": self.code,
            "message": self.message,
            "http_status": self.http_status,
            "detail": self.detail,
        }


#: Short label per code (report "by error" and badges).
LABELS = {
    "ai_disabled": _("AI disabled"),
    "no_key": _("No API key"),
    "invalid_key": _("Invalid character in the key"),
    "no_model": _("No model"),
    "agent_inactive": _("Inactive agent"),
    "empty_team": _("Empty team"),
    "skill_not_published": _("Skill without a published version"),
    "daily_cap_reached": _("Daily cap reached"),
    "empty_input": _("Empty input"),
    "key_rejected": _("Key rejected"),
    "no_permission": _("No permission for the model"),
    "unknown_model": _("Unknown model"),
    "rate_limited": _("Usage limit or credits"),
    "bad_request": _("Request rejected"),
    "provider_unavailable": _("Provider unavailable"),
    "timeout": _("Timed out"),
    "no_connection": _("No connection"),
    "incomplete_response": _("Answer cut short"),
    "invalid_json": _("Invalid JSON"),
    "refused": _("Refused by the model"),
    "provider_missing": _("Provider not installed"),
    "unexpected_error": _("Unexpected error"),
}

#: Sentences shown to users; ``%(name)s`` placeholders are filled by make().
MESSAGES = {
    "ai_disabled": _("AI is turned off in the workspace settings."),
    "no_key": _("No API key for %(provider)s. Add the key in the AI settings."),
    "no_model": _("No model chosen for this agent nor in the AI settings."),
    "agent_inactive": _("The agent “%(name)s” is inactive."),
    "empty_team": _("The coordinator “%(name)s” has no active specialist."),
    "skill_not_published": _("The required skill “%(name)s” has no published version."),
    "daily_cap_reached": _(
        "The daily AI spending cap (US$ %(cap)s) was reached. It resets "
        "tomorrow or can be changed in the AI settings."
    ),
    "empty_input": _("Enter the input text."),
    "key_rejected": _(
        "%(provider)s rejected the API key. Add a valid key in the AI settings."
    ),
    "no_permission": _(
        "The API key has no permission to use this model. Check the account "
        "plan at %(provider)s."
    ),
    "unknown_model": _(
        "%(provider)s does not know the model “%(model)s”. Check the "
        "identifier in the catalog."
    ),
    "rate_limited": _(
        "%(provider)s refused because of a usage limit or missing credits. "
        "Check the account balance and limits."
    ),
    "bad_request": _(
        "%(provider)s rejected the request parameters. The technical detail "
        "was recorded in the event."
    ),
    "provider_unavailable": _(
        "%(provider)s is unavailable right now. Try again in a few minutes."
    ),
    "timeout": _("%(provider)s did not answer in time (%(seconds)s s)."),
    "no_connection": _(
        "Could not reach %(provider)s: the server has no internet access."
    ),
    "incomplete_response": _(
        "The answer was cut by the output token limit. Raise the agent's "
        "limit or shorten the input."
    ),
    "invalid_json": _("The model did not return JSON in the requested format."),
    "refused": _("The model declined to answer this request."),
    "provider_missing": _(
        "The %(provider)s client is not installed on the server "
        "(install tripaulx-sdk[%(extra)s])."
    ),
    "unexpected_error": _("Unexpected failure calling the AI. The detail was logged."),
}


def make(
    code: str, *, http_status: int | None = None, detail: str = "", **fields: Any
) -> AIError:
    """Build the :class:`AIError` of ``code``, filling the sentence."""
    template = str(MESSAGES.get(code, MESSAGES["unexpected_error"]))
    try:
        message = template % fields
    except (KeyError, TypeError, ValueError):
        message = template
    return AIError(code=code, message=message, http_status=http_status, detail=detail)


def label(code: str) -> str:
    """Short label of ``code`` (the code itself when unknown)."""
    return str(LABELS[code]) if code in LABELS else (code or "—")


def key_complaint(api_key: str) -> str | None:
    """Return why ``api_key`` cannot go in an HTTP header, or ``None``.

    The ``Authorization`` header travels as latin-1. A character outside it
    fails before the request leaves, and the symptom looks like a provider
    error. The usual cause is pasting a look-alike letter (a Cyrillic "М"
    for "M"), so the message names the character and its position, which do
    not reveal the secret.
    """
    try:
        api_key.encode("latin-1")
    except UnicodeEncodeError as exc:
        char = api_key[exc.start]
        return str(
            _(
                "The API key has a character that cannot be sent: “%(char)s” "
                "(U+%(code)s) at position %(position)s. This usually comes "
                "from copy and paste (letters of other alphabets look the "
                "same). Add the key again in the AI settings, typed or pasted "
                "from the original source."
            )
        ) % {"char": char, "code": f"{ord(char):04X}", "position": exc.start + 1}
    return None


def code_for_status(status: int) -> str:
    """Map a provider HTTP status to our error code."""
    if status == 401:
        return "key_rejected"
    if status == 403:
        return "no_permission"
    if status == 404:
        return "unknown_model"
    if status == 429:
        return "rate_limited"
    if status >= 500:
        return "provider_unavailable"
    return "bad_request"
