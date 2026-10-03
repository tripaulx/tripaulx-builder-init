"""The backend is configured through Django 6.1 ``MAILERS`` OPTIONS."""

import django
from django.core import mail
from django.test import override_settings
import pytest

from tripaulx.mail.backends import MailgunEmailBackend

BACKEND = "tripaulx.mail.backends.MailgunEmailBackend"
LOCMEM = "django.core.mail.backends.locmem.EmailBackend"

pytestmark = pytest.mark.skipif(
    django.VERSION < (6, 1), reason="MAILERS arrived in Django 6.1"
)


def _mailers(options):
    return {"default": {"BACKEND": BACKEND, "OPTIONS": options}}


def test_options_reach_the_backend():
    options = {
        "fallback_backend": LOCMEM,
        "fallback_options": {},
        "timeout": 5,
        "fail_silently": True,
    }
    with override_settings(MAILERS=_mailers(options)):
        backend = mail.mailers["default"]
    assert isinstance(backend, MailgunEmailBackend)
    assert backend.timeout == 5
    assert backend.fail_silently is True
    assert backend.fallback_backend == LOCMEM


def test_unknown_option_is_rejected():
    with override_settings(MAILERS=_mailers({"api_key": "x"})):
        with pytest.raises(mail.InvalidMailer):
            mail.mailers["default"]


@pytest.mark.django_db
def test_send_mail_through_mailers_uses_the_fallback(public_schema):
    with override_settings(MAILERS=_mailers({"fallback_backend": LOCMEM})):
        mail.send_mail("Subject", "Body", "noreply@example.com", ["a@example.com"])
    assert mail.outbox[-1].subject == "Subject"
