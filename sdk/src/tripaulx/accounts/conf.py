"""Defaults for the accounts app, overridable through ``settings.TRIPAULX``."""

from tripaulx.core.conf import AppSettings

DAY = 24 * 60 * 60

app_settings = AppSettings(
    {
        # --- E-mail codes (verification, login 2FA, password reset) ---
        "OTP_LENGTH": 6,
        "OTP_TTL_SECONDS": 600,
        "OTP_MAX_ATTEMPTS": 5,
        # Minimum seconds between two codes of the same purpose (anti-spam).
        "OTP_RESEND_COOLDOWN": 60,
        # New accounts confirm their e-mail with a code before the first
        # login. False creates them already verified and answers signup and
        # registration with a session (e.g. while there is no e-mail provider).
        "EMAIL_VERIFICATION_REQUIRED": True,
        # Who must pass a second factor on login:
        # - "always": everyone (authenticator app, or a code by e-mail);
        # - "privileged": staff, owners and admins; other users only when
        #   they turned an authenticator app on;
        # - "optional": only users with an authenticator app.
        "MFA_POLICY": "always",
        # Signed ticket linking the password step to the second-factor step.
        "LOGIN_TICKET_TTL_SECONDS": 600,
        # --- Trusted devices ("trust this device" skips the 2FA) ---
        "TRUSTED_DEVICE_MAX_AGE": 30 * DAY,
        # --- Recovery codes ---
        "RECOVERY_CODES_QUANTITY": 9,
        # --- Authenticator app (TOTP); empty issuer means APP_NAME ---
        "TOTP_ISSUER": "",
        # --- Passkeys (WebAuthn) ---
        # Empty RP ID means the request host (each workspace subdomain). Set
        # it only to pin a parent domain shared by every subdomain.
        "WEBAUTHN_RP_ID": "",
        # Empty means APP_NAME.
        "WEBAUTHN_RP_NAME": "",
        # Extra accepted origins besides the request's own (e.g. a frontend
        # served from another origin).
        "WEBAUTHN_ORIGINS": (),
        "WEBAUTHN_CHALLENGE_TTL": 300,
        # --- Workspace signup (public schema) ---
        "SIGNUP_ENABLED": True,
        # --- Account registration (inside the current schema) ---
        # ``POST /api/auth/register/`` creates a member without an invitation
        # (consumer products). Off by default: workspaces are invite-only.
        "REGISTRATION_ENABLED": False,
        # Kinds of account the person chooses from, by key. Each one may name
        # user-model fields it accepts (``fields``) or demands (``required``):
        # {"broker": {"required": ("phone",), "fields": ("license",)}}.
        # Empty means a single kind of account and no ``profile`` input.
        "REGISTRATION_PROFILES": {},
        # User-model fields accepted (optional) whatever the profile.
        "REGISTRATION_FIELDS": (),
        # User-model field that stores the chosen profile key ("" = none; the
        # ``user_registered`` signal still carries it).
        "REGISTRATION_PROFILE_FIELD": "",
        # --- Invitations ---
        "INVITATION_TTL_SECONDS": 7 * DAY,
        # Link sent by e-mail. ``{origin}`` is the scheme and host of the
        # request that created the invitation; ``{token}`` the raw token.
        "INVITATION_ACCEPT_URL": "{origin}/accept-invitation?token={token}",
    }
)
