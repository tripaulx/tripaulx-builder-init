"""Defaults for the mail app, overridable through ``settings.TRIPAULX``."""

from tripaulx.core.conf import AppSettings

app_settings = AppSettings(
    {
        # Absolute, public URL of the logo shown at the top of HTML e-mails.
        # Empty hides the image (the product name is still shown).
        "EMAIL_LOGO_URL": "",
    }
)
