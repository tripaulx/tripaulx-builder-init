"""Concrete user model. Add project-specific fields here."""

from tripaulx.accounts.models import AbstractTripaulxUser


class User(AbstractTripaulxUser):
    """Project user: e-mail login, workspace role and security flags."""
