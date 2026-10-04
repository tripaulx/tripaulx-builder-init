"""Account routes, mounted under ``api/auth/`` on every schema."""

from django.urls import path

from . import views

app_name = "tpsdk_accounts"

urlpatterns = [
    # E-mail verification
    path("email/verify/", views.EmailVerifyView.as_view(), name="email-verify"),
    path("email/resend/", views.EmailResendView.as_view(), name="email-resend"),
    # Login + mandatory second factor
    path("login/", views.LoginView.as_view(), name="login"),
    path("login/verify/", views.LoginVerifyView.as_view(), name="login-verify"),
    path("login/resend/", views.LoginResendView.as_view(), name="login-resend"),
    path("token/refresh/", views.TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    # Passwords
    path(
        "password/reset/",
        views.PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "password/change/", views.PasswordChangeView.as_view(), name="password-change"
    ),
    path("password/rules/", views.PasswordRulesView.as_view(), name="password-rules"),
    # Second factor settings
    path(
        "mfa/recovery-codes/",
        views.RecoveryCodesView.as_view(),
        name="mfa-recovery-codes",
    ),
    path("totp/", views.TotpStatusView.as_view(), name="totp-status"),
    path("totp/setup/", views.TotpSetupView.as_view(), name="totp-setup"),
    path("totp/confirm/", views.TotpConfirmView.as_view(), name="totp-confirm"),
    path("totp/disable/", views.TotpDisableView.as_view(), name="totp-disable"),
    path("devices/", views.TrustedDeviceListView.as_view(), name="device-list"),
    path(
        "devices/<uuid:pk>/",
        views.TrustedDeviceDetailView.as_view(),
        name="device-detail",
    ),
    # Passkeys
    path(
        "passkey/register/begin/",
        views.PasskeyRegisterBeginView.as_view(),
        name="passkey-register-begin",
    ),
    path(
        "passkey/register/complete/",
        views.PasskeyRegisterCompleteView.as_view(),
        name="passkey-register-complete",
    ),
    path("passkey/credentials/", views.PasskeyListView.as_view(), name="passkey-list"),
    path(
        "passkey/credentials/<uuid:pk>/",
        views.PasskeyDetailView.as_view(),
        name="passkey-detail",
    ),
    path(
        "passkey/password-login/",
        views.PasswordLoginToggleView.as_view(),
        name="passkey-password-login",
    ),
    path(
        "passkey/login/begin/",
        views.PasskeyLoginBeginView.as_view(),
        name="passkey-login-begin",
    ),
    path(
        "passkey/login/complete/",
        views.PasskeyLoginCompleteView.as_view(),
        name="passkey-login-complete",
    ),
    # Invitations (public: the token is the credential)
    path(
        "invitations/accept/",
        views.InvitationAcceptView.as_view(),
        name="invitation-accept",
    ),
]
