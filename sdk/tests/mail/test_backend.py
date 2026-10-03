"""Mailgun backend: From header, fallback, HTTP request and failures."""

from types import SimpleNamespace
from unittest import mock
import urllib.error

from django.core import mail
from django.core.mail import EmailMultiAlternatives
import pytest

from tripaulx.mail.backends import MailgunEmailBackend

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
URLOPEN = "tripaulx.mail.backends.mailgun.urllib.request.urlopen"
CONFIG = SimpleNamespace(
    default_from_email="noreply@example.com",
    default_from_name="Acme",
    is_ready=True,
    api_key="key-123",
    domain="mg.example.com",
    base_url="https://api.mailgun.net/v3",
)


def _from(from_email, config=CONFIG):
    message = SimpleNamespace(from_email=from_email)
    return MailgunEmailBackend.from_header(config, message)


def test_bare_address_gets_the_display_name():
    assert _from("noreply@example.com") == "Acme <noreply@example.com>"


def test_named_sender_is_kept():
    assert _from("Other <x@example.com>") == "Other <x@example.com>"


def test_empty_sender_uses_the_configured_default():
    assert _from("") == "Acme <noreply@example.com>"


def test_without_configured_name_the_address_stays_bare():
    config = SimpleNamespace(default_from_email="a@example.com", default_from_name="")
    assert _from("a@example.com", config) == "a@example.com"


def _message():
    message = EmailMultiAlternatives(
        "Hi", "Plain", "noreply@example.com", ["a@example.com"], cc=["c@example.com"]
    )
    message.attach_alternative("<p>Rich</p>", "text/html")
    return message


def _backend(**options):
    return MailgunEmailBackend(fallback_backend=LOCMEM, **options)


def test_not_ready_goes_to_the_fallback():
    not_ready = SimpleNamespace(is_ready=False)
    with mock.patch("tripaulx.mail.backends.mailgun.MailgunConfig.load") as load:
        load.return_value = not_ready
        assert _backend().send_messages([_message()]) == 1
    assert mail.outbox[-1].subject == "Hi"


def test_ready_posts_to_the_mailgun_api():
    response = mock.MagicMock(status=200)
    response.__enter__.return_value = response
    with (
        mock.patch("tripaulx.mail.backends.mailgun.MailgunConfig.load") as load,
        mock.patch(URLOPEN, return_value=response) as urlopen,
    ):
        load.return_value = CONFIG
        assert _backend(timeout=3).send_messages([_message()]) == 1
    request = urlopen.call_args.args[0]
    assert request.full_url == "https://api.mailgun.net/v3/mg.example.com/messages"
    assert request.get_header("Authorization").startswith("Basic ")
    body = request.data.decode()
    for part in ("Acme <noreply@example.com>", "a@example.com", "c@example.com"):
        assert part in body
    assert "<p>Rich</p>" in body and 'name="subject"' in body
    assert urlopen.call_args.kwargs["timeout"] == 3
    assert mail.outbox == []


@pytest.mark.parametrize("silent", [True, False])
def test_http_failure(silent):
    error = urllib.error.URLError("down")
    with (
        mock.patch("tripaulx.mail.backends.mailgun.MailgunConfig.load") as load,
        mock.patch(URLOPEN, side_effect=error),
    ):
        load.return_value = CONFIG
        backend = _backend(fail_silently=silent)
        if silent:
            assert backend.send_messages([_message()]) == 0
        else:
            with pytest.raises(urllib.error.URLError):
                backend.send_messages([_message()])


def test_no_messages_sends_nothing():
    assert _backend().send_messages([]) == 0
