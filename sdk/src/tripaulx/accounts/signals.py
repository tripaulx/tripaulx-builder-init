"""Signals sent by the accounts app.

- ``user_signed_up``: a workspace owner signed up (``user``, ``workspace``).
- ``user_logged_in_2fa``: a login completed its second factor and received
  tokens (``user``, ``request``, ``method``: ``totp``, ``email``,
  ``recovery_code``, ``trusted_device`` or ``passkey``).
"""

from django.dispatch import Signal

user_signed_up = Signal()
user_logged_in_2fa = Signal()
