"""E-mail backends of the mail app."""

from .mailgun import MailgunEmailBackend

__all__ = ["MailgunEmailBackend"]
