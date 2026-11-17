# Accounts, signup and e-mail

`tripaulx.accounts` covers workspace signup, self-service account registration,
login with a second factor (mandatory by default), authenticator apps (TOTP), passkeys, recovery codes, trusted devices,
password reset and change, workspace members and invitations.
`tripaulx.mail` sends the e-mails through Mailgun.

Portuguese version: [pt-BR/accounts.md](pt-BR/accounts.md).

## Wiring

The project template already does all of this.

```python
# config/settings/base_parts/rest.py
from tripaulx.settings.rest import rest_framework, simple_jwt, spectacular

REST_FRAMEWORK = rest_framework()  # TenantJWTAuthentication, throttles
SIMPLE_JWT = simple_jwt(get_env("JWT_SIGNING_KEY", ""))  # empty: SECRET_KEY
SPECTACULAR_SETTINGS = spectacular("Acme API")  # docs for admins only
```

```python
# config/urls.py (workspaces)
(path("api/auth/", include("tripaulx.accounts.api.urls")),)
(path("api/workspace/", include("tripaulx.accounts.api.urls_workspace")),)

# config/urls_public.py (apex domain)
(path("api/auth/", include("tripaulx.accounts.api.urls_public")),)  # signup
(path("api/auth/", include("tripaulx.accounts.api.urls")),)
```

`tripaulx.settings.apps` installs `rest_framework`, `drf_spectacular`,
`corsheaders`, `rest_framework_simplejwt.token_blacklist` (in every schema,
next to the users) and `tripaulx.mail` (public schema only).

## Flows

### Signup (public schema)

1. `POST /api/auth/signup/` with
   `{email, full_name, password, password_confirm, workspace_name, slug?}`.
   The full name is split into `first_name` (first word) and `last_name`
   (the rest).
   Without `slug`, it is derived from the name (`Acme Ltda` → `acme_ltda`).
2. The SDK validates the slug (reserved words, pattern, availability) and the
   password (see [Password rules](#password-rules)), then creates the `Workspace`, its schema (all tenant migrations)
   and the `Domain` `<slug>.<BASE_DOMAIN>` in a single transaction.
3. Inside the new schema it creates the owner (`role=owner`,
   `email_verified=False`) and e-mails the verification code.
4. The answer is `201` with `workspace_slug`, `workspace_name`,
   `workspace_domain`, `workspace_url`, `api_url`, `email`,
   `email_verification_required` and `session` (`null` while the e-mail must
   be verified).
5. Signals: `tripaulx.tenants.signals.workspace_created` (after commit) and
   `tripaulx.accounts.signals.user_signed_up`.

Creating a schema takes about one second with the SDK apps; it grows with the
project's tenant migrations. Signup is guarded by `SIGNUP_ENABLED` and by the
`auth_register` throttle.

`GET /api/auth/workspaces/<slug>/` (public schema, anonymous, throttle
`auth_lookup`) answers the "which workspace?" and "is this address free?"
screens: `{slug, exists, available, name, reason, workspace_url, api_url}`.

### Registration (inside a workspace)

Signup creates a workspace. Registration adds a person to the workspace being
visited, without an invitation: it is meant for consumer products (a portal
whose visitors create accounts) and is **off by default**.

1. `POST /api/auth/register/` with
   `{email, full_name, password, password_confirm, profile?, ...extra fields}`.
2. The SDK validates the person and the password, the profile and its extra
   fields, then creates the user with `role=member` and e-mails the
   verification code.
3. The answer is `201` with `email`, `profile`, `email_verification_required`
   and `session`. The person confirms the code on `email/verify/`, which logs
   them in.
4. An e-mail that already has an account answers `400` with `field: "email"`.
   If that account is still unverified, a new code is sent and the answer
   carries `email_verification_required: true`, so the client opens the code
   screen. The first password is never replaced.
5. Signal: `tripaulx.accounts.signals.user_registered` (`user`, `profile`,
   `extra`).

**Profiles** are the kinds of account a person chooses from. Extra fields are
fields of the project's `User` model and are validated by the model field
itself (type, length, validators), so the rule lives in one place:

```python
# users/models.py
class User(AbstractTripaulxUser):
    phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])
    account_type = models.CharField(max_length=16, blank=True)


# config/settings/base_parts/tripaulx.py
TRIPAULX = {
    "REGISTRATION_ENABLED": True,
    "REGISTRATION_PROFILES": {
        "buyer": {},
        "owner": {"required": ("phone",)},
        "broker": {"required": ("phone",), "fields": ("license",)},
    },
    "REGISTRATION_FIELDS": ("phone",),  # optional for every profile
    "REGISTRATION_PROFILE_FIELD": "account_type",  # where the key is stored
}
```

With profiles configured, `profile` is required and must be one of the keys.
Fields a profile does not list are ignored. Registration never writes `role`,
`is_staff`, `is_superuser`, `email_verified` or the other access fields:
naming one of them in the settings raises `ImproperlyConfigured`.

Roles and profiles are different things. The role (`owner`, `admin`,
`member`) is the permission inside the workspace; the profile is what kind of
customer the person is. Registered people are always members.

### What a client needs first

`GET /api/auth/config/` (anonymous, every schema) returns the flags a client
reads before rendering its screens: `signup_enabled`, `registration_enabled`,
`registration_profiles` (key, required and optional fields),
`registration_fields`, `email_verification_required`, `email_available`
(whether sent e-mail reaches anyone), `mfa_policy`, `base_domain` and
`workspace_origin_template` (`https://{subdomain}.example.com`).

### E-mail verification

`POST /api/auth/email/verify/` with `{email, code}` marks the address as
verified and returns the tokens (the code is the proof of the inbox).
`POST /api/auth/email/resend/` sends a new code; the answer is always the
same, whether the account exists or not.

With `EMAIL_VERIFICATION_REQUIRED` off (for example while there is no e-mail
provider), signup and registration create the account already verified, send
no code and answer with `session` (`access`, `refresh`, `user`); login no
longer asks unverified accounts for the code.

### Login and the second factor

1. `POST /api/auth/login/` with `{email, password, device_token?}`.
   - Wrong credentials: `401`.
   - Passkey-only account (correct password): `403` with `passkey_required`.
   - Unverified e-mail: `403` with `email_verification_required` (a code is
     sent).
   - A valid `device_token` (trusted device) skips the second factor and
     returns the tokens.
   - Otherwise: `{mfa_required, ticket, mfa_method}`. `mfa_method` is `totp`
     when the authenticator app is confirmed (no e-mail is sent), else
     `email` (with `masked_email`).
2. `POST /api/auth/login/verify/` with `{ticket, code, trust_device?,
   device_label?}`. The `code` field accepts the app code, the e-mailed code
   or a recovery code. With `trust_device`, the answer carries
   `device_token` and `device_token_max_age`.
3. `POST /api/auth/login/resend/` with `{ticket}` sends a new e-mail code
   (never for app users; same answer in every case).

The ticket is signed, expires after `LOGIN_TICKET_TTL_SECONDS` and is bound
to the schema. Privileged accounts (owner, admin, staff) without an app or a
passkey get `mfa_setup_required: true` in the user payload so clients can ask
them for a strong factor.

`MFA_POLICY` decides who gets the second step:

| Value | Who must pass a second factor |
|---|---|
| `always` (default) | Everyone |
| `privileged` | Staff, owners and admins; other users log in with the password |
| `optional` | Nobody |

Whatever the policy, a user who turned an authenticator app on is always
asked for it, and an unknown value counts as `always`. When no second factor
is due, `login/` answers with the tokens at once and the
`user_logged_in_2fa` signal reports `method="password"`.

### Tokens bound to the workspace

Every JWT carries a `schema` claim. `TenantJWTAuthentication` refuses a token
issued in another schema (user ids repeat across schemas), and so do refresh
and logout (`TenantRefreshToken`). Access lasts 30 minutes, refresh 12 hours,
with rotation and blacklist. Refresh has its own throttle (`auth_refresh`).

### Authenticator app (TOTP)

Hand-written RFC 6238 (checked against the RFC vectors), 6 digits, 30-second
steps, one step of tolerance, anti-replay. The secret is stored encrypted.

- `POST /api/auth/totp/setup/` returns `secret`, `otpauth_uri` and `qr_svg`
  (only here); `DELETE` cancels a pending setup.
- `POST /api/auth/totp/confirm/` with the first code activates it and returns
  9 recovery codes, shown once.
- `POST /api/auth/totp/disable/` needs an app code or a recovery code.
- `GET /api/auth/totp/` returns the status.

### Recovery codes

Format `XXXXX-XXXXX` without look-alike characters, stored as hashes, single
use. A new list burns the previous one. `GET /api/auth/mfa/recovery-codes/`
counts them, `POST` generates a new list (`quantity` 1–20). Operators can
run `manage.py generate_recovery_codes --schema acme --user jane@example.com`.

### Passkeys (WebAuthn)

- Register (logged in): `POST passkey/register/begin/`, then
  `POST passkey/register/complete/` with `{credential, name}`.
- Login: `POST passkey/login/begin/` with an optional `email`, then
  `POST passkey/login/complete/` with `{ticket, credential}`. The e-mail must
  be verified here too.
- Manage: `GET passkey/credentials/`, `PATCH passkey/credentials/<id>/`
  (rename), `DELETE passkey/credentials/<id>/`.
- Passkey-only: `POST passkey/password-login/` with `{disabled: true}`. It
  needs a passkey; it only applies while one exists; the last passkey cannot
  be removed while password login is off.

The RP ID is the request host (each workspace subdomain), unless
`WEBAUTHN_RP_ID` pins a parent domain. Challenges live in the Django cache:
**production with more than one worker needs a shared cache (Redis,
`REDIS_URL`)**, or a "complete" may reach a worker that never saw the
challenge.

### Trusted devices

`GET /api/auth/devices/` lists the active ones (never the token);
`DELETE /api/auth/devices/<id>/` revokes one.

### Passwords

- `POST /api/auth/password/reset/` with `{email}` e-mails a code (silent for
  unknown addresses).
- `POST /api/auth/password/reset/confirm/` with
  `{email, code, password, password_confirm}`.
  The password is validated before the code is consumed; every failure has
  the same message.
- `POST /api/auth/password/change/` with
  `{current_password, new_password, new_password_confirm}` (logged in) returns a
  fresh token pair.

Reset and change revoke every trusted device and blacklist every refresh
token of the user.

### Password rules

Every place that sets a password requires a matching confirmation and runs the
project's `AUTH_PASSWORD_VALIDATORS` *against the person*: e-mail, first name
and last name. So `UserAttributeSimilarityValidator` rejects a password close
to the user's own data, even at signup, before the user exists. This applies to
signup, password reset, password change, invitation acceptance and
`create_workspace_admin`.

- A mismatch answers `400` with `field: "password_confirm"`; a broken rule
  answers `field: "password"` with the validators' (translated) messages.
- `GET /api/auth/password/rules/` (anonymous) returns `{"rules": [...]}`, the
  validators' help texts in the request language, for forms to show up front.

### The first administrator of a workspace

`manage.py create_workspace_admin --schema <slug>` asks for e-mail, full name
and the password twice. The password is hidden, the rules are shown first and
the question repeats when a rule fails. It creates an owner with a verified
e-mail and Django admin access.
- Options: `--email`, `--full-name`, `--role owner|admin|member`, `--no-superuser`.
- `--password-stdin` reads the password from stdin, for scripts.
- `--if-none` does nothing when the workspace already has an owner.

In generated projects, `./start setup` runs it with `--if-none` for the first
workspace when it runs in a terminal (onboarding). `./start admin` runs it at
any time.

### Members and invitations (owners and admins)

Permission: `tripaulx.accounts.api.permissions.IsWorkspaceAdmin`.

- `GET /api/workspace/members/`, `GET|PATCH|DELETE
  /api/workspace/members/<id>/` (PATCH `{role}`; DELETE deactivates and ends
  the sessions), `POST /api/workspace/members/<id>/reactivate/` gives a
  deactivated member access again, with the same role.
- `GET|POST /api/workspace/invitations/` (`{email, role}`),
  `DELETE /api/workspace/invitations/<id>/` revokes.
- `POST /api/auth/invitations/accept/` (anonymous) with `{token, password,
  password_confirm, full_name?}` (or `first_name?`/`last_name?`) creates the user with a verified e-mail and the
  invited role, and returns the tokens.

Rules: only an owner changes an owner or grants the owner role; the
workspace always keeps one active owner. The invitation link is
`INVITATION_ACCEPT_URL` formatted with the request origin and the token.

## Endpoint summary

| Method | Path (`/api/auth/` unless noted) | Auth |
|---|---|---|
| GET | `config/` | anonymous |
| POST | `signup/` (public schema) | anonymous |
| GET | `workspaces/<slug>/` (public schema) | anonymous |
| POST | `register/` (`REGISTRATION_ENABLED`) | anonymous |
| POST | `email/verify/`, `email/resend/` | anonymous |
| POST | `login/`, `login/verify/`, `login/resend/` | anonymous |
| POST | `token/refresh/` | refresh token |
| POST | `logout/` | JWT |
| GET | `me/` | JWT |
| POST | `password/reset/`, `password/reset/confirm/` | anonymous |
| POST | `password/change/` | JWT |
| GET | `password/rules/` | anonymous |
| GET, POST | `mfa/recovery-codes/` | JWT |
| GET / POST, DELETE / POST / POST | `totp/`, `totp/setup/`, `totp/confirm/`, `totp/disable/` | JWT |
| GET / DELETE | `devices/`, `devices/<id>/` | JWT |
| POST | `passkey/register/begin/`, `passkey/register/complete/` | JWT |
| GET / PATCH, DELETE | `passkey/credentials/`, `passkey/credentials/<id>/` | JWT |
| POST | `passkey/password-login/` | JWT |
| POST | `passkey/login/begin/`, `passkey/login/complete/` | anonymous |
| POST | `invitations/accept/` | anonymous |
| GET / GET, PATCH, DELETE / POST | `/api/workspace/members/`, `.../<id>/`, `.../<id>/reactivate/` | owner/admin |
| GET, POST / DELETE | `/api/workspace/invitations/`, `.../<id>/` | owner/admin |

## Settings (`TRIPAULX`)

| Key | Default | Meaning |
|---|---|---|
| `APP_NAME` | `"App"` | Brand in e-mails, TOTP issuer and passkey RP name |
| `FIELD_ENCRYPTION_KEY` | `""` | Fernet key; empty derives one from `SECRET_KEY` (dev only) |
| `EMAIL_LOGO_URL` | `""` | Logo at the top of HTML e-mails |
| `OTP_LENGTH` | `6` | Digits of e-mail codes |
| `OTP_TTL_SECONDS` | `600` | Lifetime of e-mail codes |
| `OTP_MAX_ATTEMPTS` | `5` | Wrong guesses before a code dies |
| `OTP_RESEND_COOLDOWN` | `60` | Seconds between two codes of the same purpose |
| `LOGIN_TICKET_TTL_SECONDS` | `600` | Lifetime of the login ticket |
| `TRUSTED_DEVICE_MAX_AGE` | 30 days | Lifetime of a trusted device |
| `RECOVERY_CODES_QUANTITY` | `9` | Default size of a recovery-code list |
| `TOTP_ISSUER` | `""` | Issuer in the app; empty uses `APP_NAME` |
| `WEBAUTHN_RP_ID` | `""` | Empty uses the request host |
| `WEBAUTHN_RP_NAME` | `""` | Empty uses `APP_NAME` |
| `WEBAUTHN_ORIGINS` | `()` | Extra accepted origins |
| `WEBAUTHN_CHALLENGE_TTL` | `300` | Seconds a challenge stays in the cache |
| `SIGNUP_ENABLED` | `True` | Public signup on/off |
| `EMAIL_VERIFICATION_REQUIRED` | `True` | New accounts confirm the e-mail by code; off answers with a session |
| `MFA_POLICY` | `"always"` | Who must pass a second factor: `always`, `privileged` or `optional` |
| `REGISTRATION_ENABLED` | `False` | Self-service accounts inside a workspace |
| `REGISTRATION_PROFILES` | `{}` | Kinds of account: `{key: {"required": (...), "fields": (...)}}` |
| `REGISTRATION_FIELDS` | `()` | User-model fields accepted for every profile |
| `REGISTRATION_PROFILE_FIELD` | `""` | User-model field that stores the profile key |
| `INVITATION_TTL_SECONDS` | 7 days | Lifetime of an invitation |
| `INVITATION_ACCEPT_URL` | `"{origin}/accept-invitation?token={token}"` | Link in the invitation e-mail |

Throttle scopes (`rest_framework()`): `anon` 100/hour, `user` 1000/hour,
`auth_login` 10/min, `auth_register` 5/min, `auth_otp` 10/min,
`auth_lookup` 60/min, `auth_refresh` 60/min. Override one with
`rest_framework(DEFAULT_THROTTLE_RATES={"anon": "50/hour"})`.

## E-mail

Templates live in `templates/tripaulx/mail/`: `base.html`, `code_base.*`,
`email_verify.*`, `login_2fa.*`, `password_reset.*` and `invite.*` (`.html`
and `.txt`). A project overrides any of them by creating the same path in its
own `templates/` folder. The context has `app_name` and `logo_url`.

The Mailgun backend reads its configuration from the `MailgunConfig`
singleton (public admin; the API key is encrypted with `core.crypto`). Until
it is enabled with a key and a domain, messages go to the fallback backend.

```python
MAILERS = {
    "default": {
        "BACKEND": "tripaulx.mail.backends.MailgunEmailBackend",
        "OPTIONS": {
            "fallback_backend": "django.core.mail.backends.smtp.EmailBackend",
            "fallback_options": {"host": "smtp.example.com", "port": 587},
            "timeout": 10,
        },
    },
}
```

Every `OPTIONS` key is a keyword argument of the backend; Django rejects
unknown ones.

Tools to check the setup:

- `tripaulx.mail.services.email_available()` tells whether sent e-mail
  reaches anyone: Mailgun ready, an SMTP host, or a local backend (console,
  locmem, file). `GET /api/auth/config/` exposes it as `email_available`.
- `manage.py send_test_mail --to you@example.com [--template invite]
  [--lang pt-br]` sends one of the e-mails with sample data.
- `path("__mail/", include("tripaulx.mail.urls"))` in the public URLconf
  previews an e-mail in the browser at `/__mail/<name>/?lang=pt-br&format=txt`
  (404 unless `DEBUG`).
- A project registers samples for its own e-mails with
  `tripaulx.mail.services.register_sample("monthly_report", lambda: {...})`.

## Encrypted fields

`tripaulx.core.crypto.encrypt()` / `decrypt()` use Fernet with
`FIELD_ENCRYPTION_KEY`. `decrypt()` logs and returns `""` when the key is
wrong. The template's `prod.py` calls `validate_field_key()`, so production
does not start without a valid key; `./start` generates one in `.env.local`.

## Tests

`tripaulx.core.testing.TenantAPITestCase` gives `api_client(user=None)` (a
DRF client on the tenant domain with a schema-bound JWT) and
`anon_api_client()`.
