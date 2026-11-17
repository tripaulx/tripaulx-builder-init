"""Registration profiles: the kinds of account and the fields each accepts.

Configured by ``REGISTRATION_PROFILES``, ``REGISTRATION_FIELDS`` and
``REGISTRATION_PROFILE_FIELD``. Extra fields are user-model fields and are
validated by the model field itself (its type, length and validators), so
the rule lives in one place: the project's ``User`` model.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import (
    FieldDoesNotExist,
    ImproperlyConfigured,
    ValidationError,
)
from django.utils.translation import gettext as _

from ..conf import app_settings
from .errors import SignupError

#: Fields registration never writes, whatever the settings say: they grant
#: access or belong to the login flows.
PROTECTED_FIELDS = frozenset(
    {
        "id",
        "pk",
        "email",
        "password",
        "role",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "is_active",
        "email_verified",
        "password_login_disabled",
        "groups",
        "user_permissions",
        "last_login",
        "date_joined",
    }
)


def profiles() -> dict[str, dict[str, tuple[str, ...]]]:
    """Return the configured profiles as ``{key: {"required", "fields"}}``."""
    found: dict[str, dict[str, tuple[str, ...]]] = {}
    for key, spec in dict(app_settings.REGISTRATION_PROFILES or {}).items():
        spec = spec or {}
        found[str(key)] = {
            "required": tuple(spec.get("required", ())),
            "fields": tuple(spec.get("fields", ())),
        }
    return found


def _model_field(name: str) -> Any:
    """Return the user-model field ``name``; refuse protected or unknown ones."""
    if name in PROTECTED_FIELDS:
        raise ImproperlyConfigured(
            f"Registration cannot write the user field {name!r}."
        )
    try:
        return get_user_model()._meta.get_field(name)
    except FieldDoesNotExist as exc:
        raise ImproperlyConfigured(
            f"Registration field {name!r} is not a field of the user model."
        ) from exc


def clean_profile(profile: str) -> str:
    """Return the chosen profile key ("" when the project has no profiles).

    Raises:
        SignupError: profiles exist and ``profile`` is not one of them.
    """
    known = profiles()
    if not known:
        return ""
    if profile not in known:
        raise SignupError(_("Choose the kind of account."), field="profile")
    return profile


def accepted_fields(profile: str = "") -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return ``(required, optional)`` extra field names for ``profile``."""
    spec = profiles().get(profile, {"required": (), "fields": ()})
    required = tuple(dict.fromkeys(spec["required"]))
    optional = (*spec["fields"], *app_settings.REGISTRATION_FIELDS)
    return required, tuple(n for n in dict.fromkeys(optional) if n not in required)


def all_field_names() -> tuple[str, ...]:
    """Return every extra field name any profile may send."""
    names: list[str] = list(app_settings.REGISTRATION_FIELDS)
    for spec in profiles().values():
        names += [*spec["required"], *spec["fields"]]
    return tuple(dict.fromkeys(names))


def _clean_value(name: str, raw: Any) -> Any:
    """Validate ``raw`` with the model field ``name``."""
    try:
        return _model_field(name).clean(raw, None)
    except ValidationError as exc:
        raise SignupError(" ".join(exc.messages), field=name) from exc


def clean_extra(profile: str, data: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the extra fields of ``profile``; return the values to store.

    Fields the profile does not accept are ignored. The profile key itself is
    added under ``REGISTRATION_PROFILE_FIELD`` when that setting is set.

    Raises:
        SignupError: a required field is missing or a value is invalid.
    """
    required, optional = accepted_fields(profile)
    cleaned: dict[str, Any] = {}
    for name in required:
        raw = data.get(name)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            raise SignupError(_("This field is required."), field=name)
        cleaned[name] = _clean_value(name, raw)
    for name in optional:
        raw = data.get(name)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        cleaned[name] = _clean_value(name, raw)
    target = app_settings.REGISTRATION_PROFILE_FIELD
    if target and profile:
        cleaned[target] = _clean_value(target, profile)
    return cleaned
