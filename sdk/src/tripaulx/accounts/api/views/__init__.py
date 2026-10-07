"""Views of the accounts API, one module per flow."""

from .devices import TrustedDeviceDetailView, TrustedDeviceListView
from .email import EmailResendView, EmailVerifyView
from .invitations import InvitationAcceptView, InvitationDetailView, InvitationListView
from .login import LoginResendView, LoginVerifyView, LoginView
from .members import MemberDetailView, MemberListView, MemberReactivateView
from .mfa import (
    RecoveryCodesView,
    TotpConfirmView,
    TotpDisableView,
    TotpSetupView,
    TotpStatusView,
)
from .passkeys import (
    PasskeyDetailView,
    PasskeyListView,
    PasskeyLoginBeginView,
    PasskeyLoginCompleteView,
    PasskeyRegisterBeginView,
    PasskeyRegisterCompleteView,
    PasswordLoginToggleView,
)
from .password import (
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordRulesView,
)
from .session import LogoutView, MeView, TokenRefreshView
from .signup import SignupView

__all__ = [
    "EmailResendView",
    "EmailVerifyView",
    "InvitationAcceptView",
    "InvitationDetailView",
    "InvitationListView",
    "LoginResendView",
    "LoginVerifyView",
    "LoginView",
    "LogoutView",
    "MeView",
    "MemberDetailView",
    "MemberListView",
    "MemberReactivateView",
    "PasskeyDetailView",
    "PasskeyListView",
    "PasskeyLoginBeginView",
    "PasskeyLoginCompleteView",
    "PasskeyRegisterBeginView",
    "PasskeyRegisterCompleteView",
    "PasswordChangeView",
    "PasswordLoginToggleView",
    "PasswordResetConfirmView",
    "PasswordResetRequestView",
    "PasswordRulesView",
    "RecoveryCodesView",
    "SignupView",
    "TokenRefreshView",
    "TotpConfirmView",
    "TotpDisableView",
    "TotpSetupView",
    "TotpStatusView",
    "TrustedDeviceDetailView",
    "TrustedDeviceListView",
]
