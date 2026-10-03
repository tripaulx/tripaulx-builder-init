"""Business logic of the mail app."""

from .templated import brand_context, render_mail, send_templated_mail

__all__ = ["brand_context", "render_mail", "send_templated_mail"]
