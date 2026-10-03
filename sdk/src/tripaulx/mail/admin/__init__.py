"""Admin registrations of the mail app (public schema)."""

from .mailgun_config import MailgunConfigAdmin, MailgunConfigForm

__all__ = ["MailgunConfigAdmin", "MailgunConfigForm"]
