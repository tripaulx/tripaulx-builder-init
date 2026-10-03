"""Registration and authentication ceremonies (py_webauthn wrappers)."""

from __future__ import annotations

import json
import secrets
from typing import Any

from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _
from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from ...models import WebAuthnCredential
from ..errors import PasskeyError
from . import relying_party as rp


def _descriptors(user: Any) -> list[PublicKeyCredentialDescriptor]:
    """Return the user's existing credentials (to exclude or allow)."""
    return [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred.credential_id))
        for cred in user.passkeys.all()
    ]


def registration_options(user: Any, request: HttpRequest) -> dict[str, Any]:
    """Return registration options and remember the challenge for ``user``."""
    options = generate_registration_options(
        rp_id=rp.rp_id_for(request),
        rp_name=rp.rp_name(),
        user_id=str(user.pk).encode(),
        user_name=user.email,
        user_display_name=user.get_full_name() or user.email,
        exclude_credentials=_descriptors(user),
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    rp.store_challenge(
        f"{rp.REGISTRATION_PREFIX}{user.pk}", bytes_to_base64url(options.challenge)
    )
    return json.loads(options_to_json(options))


def verify_registration(
    user: Any, credential: str, name: str, *, request: HttpRequest
) -> WebAuthnCredential:
    """Verify the browser's registration response and store the passkey."""
    challenge = rp.pop_challenge(f"{rp.REGISTRATION_PREFIX}{user.pk}")
    if not challenge:
        raise PasskeyError(_("The challenge expired. Try again."))
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=rp.rp_id_for(request),
            expected_origin=rp.expected_origins_for(request),
            require_user_verification=False,
        )
    except Exception as exc:  # noqa: BLE001 - any library failure is a refusal
        raise PasskeyError(_("Could not register the passkey.")) from exc
    return WebAuthnCredential.objects.create(
        user=user,
        credential_id=bytes_to_base64url(verified.credential_id),
        public_key=bytes_to_base64url(verified.credential_public_key),
        sign_count=verified.sign_count,
        aaguid=str(verified.aaguid or ""),
        name=(name or "Passkey")[:120],
    )


def authentication_options(
    user: Any = None, *, request: HttpRequest
) -> tuple[str, dict[str, Any]]:
    """Return ``(ticket, options)``; without ``user``, any passkey may answer.

    The ticket links "begin" to "complete" through the cache.
    """
    options = generate_authentication_options(
        rp_id=rp.rp_id_for(request),
        allow_credentials=(_descriptors(user) if user is not None else None) or None,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    ticket = secrets.token_urlsafe(24)
    rp.store_challenge(
        f"{rp.AUTHENTICATION_PREFIX}{ticket}", bytes_to_base64url(options.challenge)
    )
    return ticket, json.loads(options_to_json(options))


def verify_authentication(
    ticket: str, credential: str, *, request: HttpRequest
) -> WebAuthnCredential:
    """Verify an authentication response; update and return the credential."""
    challenge = rp.pop_challenge(f"{rp.AUTHENTICATION_PREFIX}{ticket}")
    if not challenge:
        raise PasskeyError(_("The challenge expired. Try again."))
    try:
        raw_id = json.loads(credential)["id"]
    except (ValueError, KeyError, TypeError) as exc:
        raise PasskeyError(_("Invalid credential.")) from exc
    stored = (
        WebAuthnCredential.objects.filter(credential_id=raw_id)
        .select_related("user")
        .first()
    )
    if stored is None:
        raise PasskeyError(_("Passkey not recognized."))
    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=rp.rp_id_for(request),
            expected_origin=rp.expected_origins_for(request),
            credential_public_key=base64url_to_bytes(stored.public_key),
            credential_current_sign_count=stored.sign_count,
            require_user_verification=False,
        )
    except Exception as exc:  # noqa: BLE001 - any library failure is a refusal
        raise PasskeyError(_("Passkey authentication failed.")) from exc
    stored.sign_count = verified.new_sign_count
    stored.last_used_at = timezone.now()
    stored.save(update_fields=["sign_count", "last_used_at", "updated_at"])
    return stored
