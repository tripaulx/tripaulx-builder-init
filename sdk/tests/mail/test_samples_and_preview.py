"""Sample contexts, the DEBUG preview and the ``send_test_mail`` command."""

from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import Http404
from django.test import RequestFactory, override_settings
import pytest

from tripaulx.mail.services import (
    register_sample,
    render_mail,
    sample_context,
    sample_names,
)
from tripaulx.mail.views import preview

SDK_MAILS = ("email_verify", "invite", "login_2fa", "password_reset")


def test_every_sdk_mail_has_a_sample_that_renders():
    assert set(SDK_MAILS) <= set(sample_names())
    for name in SDK_MAILS:
        text, html = render_mail(name, sample_context(name))
        assert text.strip() and "<html" in html.lower()


def test_projects_register_their_own_samples():
    register_sample("login_2fa_copy", lambda: sample_context("login_2fa"))
    assert "login_2fa_copy" in sample_names()
    assert sample_context("login_2fa_copy")["code"] == "482915"


def test_preview_is_debug_only():
    request = RequestFactory().get("/__mail/login_2fa/")
    with pytest.raises(Http404):
        preview(request, "login_2fa")
    with override_settings(DEBUG=True):
        assert "4 8 2 9 1 5" in preview(request, "login_2fa").content.decode()
        text = preview(RequestFactory().get("/", {"format": "txt"}), "login_2fa")
        assert text["Content-Type"].startswith("text/plain")
        with pytest.raises(Http404):
            preview(request, "no_such_mail")


@pytest.mark.django_db
def test_send_test_mail_command():
    out = StringIO()
    call_command("send_test_mail", "--to", "you@example.com", stdout=out)
    assert mail.outbox[-1].to == ["you@example.com"]
    assert mail.outbox[-1].subject == "[test] password_reset"
    assert "1 message(s)" in out.getvalue()
    with pytest.raises(CommandError):
        call_command("send_test_mail", "--to", "x@example.com", "--template", "nope")
