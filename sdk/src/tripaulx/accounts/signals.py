"""Signals sent by the accounts app.

- ``user_signed_up``: a workspace owner signed up (``user``, ``workspace``).
- ``user_registered``: a person registered an account in the current schema
  (``user``, ``profile``: the chosen profile key or ``""``, ``extra``: the
  accepted extra fields).
- ``user_logged_in_2fa``: a login completed and received tokens (``user``,
  ``request``, ``method``: ``totp``, ``email``, ``recovery_code``,
  ``trusted_device``, ``passkey``, ``email_verify``, ``invitation``, or
  ``password``, ``signup`` and ``registration`` when no second factor was
  due).
"""

from django.dispatch import Signal

user_signed_up = Signal()
user_registered = Signal()
user_logged_in_2fa = Signal()
