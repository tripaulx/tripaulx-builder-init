"""``email_available`` tells whether sent e-mail reaches anyone."""

import django
from django.test import override_settings
import pytest

from tripaulx.mail.models import MailgunConfig
from tripaulx.mail.services import email_available

MAILGUN = "tripaulx.mail.backends.MailgunEmailBackend"
SMTP = "django.core.mail.backends.smtp.EmailBackend"
DUMMY = "django.core.mail.backends.dummy.EmailBackend"
LOCMEM = "django.core.mail.backends.locmem.EmailBackend"

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(django.VERSION < (6, 1), reason="MAILERS arrived in 6.1"),
]


def mailer(backend, **options):
    return override_settings(
        MAILERS={"default": {"BACKEND": backend, "OPTIONS": options}}
    )


def test_local_backends_count_as_available():
    with mailer(LOCMEM):
        assert email_available() is True


def test_smtp_needs_a_host():
    with mailer(SMTP, host=""):
        assert email_available() is False
    with mailer(SMTP, host="smtp.example.com"):
        assert email_available() is True


def test_unknown_backend_is_unavailable():
    with mailer(DUMMY):
        assert email_available() is False


def test_mailgun_follows_its_configuration_then_its_fallback(public_schema):
    with mailer(MAILGUN, fallback_backend=DUMMY):
        assert email_available() is False
        config = MailgunConfig.load()
        config.enabled, config.domain, config.api_key = True, "mg.example.com", "key"
        config.save()
        assert email_available() is True
    MailgunConfig.objects.all().delete()
    with mailer(MAILGUN, fallback_backend=SMTP, fallback_options={"host": "x"}):
        assert email_available() is True
    with mailer(MAILGUN, fallback_backend=SMTP, fallback_options={}):
        assert email_available() is False
    with mailer(MAILGUN):
        assert email_available() is True
