"""Admin of the accounts app.

The security records are registered here; the user admin base class is
registered by each project for its concrete user model.
"""

from .security import (
    EmailCodeAdmin,
    InvitationAdmin,
    RecoveryCodeAdmin,
    TotpDeviceAdmin,
    TrustedDeviceAdmin,
    WebAuthnCredentialAdmin,
)
from .user import TripaulxUserAdmin

__all__ = [
    "EmailCodeAdmin",
    "InvitationAdmin",
    "RecoveryCodeAdmin",
    "TotpDeviceAdmin",
    "TripaulxUserAdmin",
    "TrustedDeviceAdmin",
    "WebAuthnCredentialAdmin",
]
