"""Business logic of the mail app."""

from .availability import email_available
from .samples import register_sample, sample_context, sample_names
from .templated import brand_context, render_mail, send_templated_mail

__all__ = [
    "brand_context",
    "email_available",
    "register_sample",
    "render_mail",
    "sample_context",
    "sample_names",
    "send_templated_mail",
]
