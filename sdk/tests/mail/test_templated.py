"""Branded, overridable e-mail templates."""

from django.core import mail
from django.test import override_settings

from tripaulx.mail.services import brand_context, render_mail, send_templated_mail

BRAND = {"APP_NAME": "Acme", "EMAIL_LOGO_URL": "https://example.com/logo.png"}
CONTEXT = {"code": "123456", "code_spaced": "1 2 3 4 5 6", "minutes": 10}


@override_settings(TRIPAULX=BRAND)
def test_brand_comes_from_settings():
    assert brand_context() == {
        "app_name": "Acme",
        "logo_url": "https://example.com/logo.png",
    }
    text, html = render_mail("login_2fa", CONTEXT)
    assert '<img src="https://example.com/logo.png"' in html
    assert "1 2 3 4 5 6" in html and "Acme" in html
    assert "123456" in text and "10 minutes" in text


@override_settings(TRIPAULX={"APP_NAME": "Acme"})
def test_without_logo_the_name_is_shown():
    _text, html = render_mail("email_verify", {**CONTEXT, "first_name": "Jane"})
    assert "<img" not in html
    assert "Hello Jane," in html


def test_text_body_is_not_html_escaped():
    text, _html = render_mail("invite", {"url": "https://x.test/?a=1&b=2", "days": 7})
    assert "https://x.test/?a=1&b=2" in text


def test_send_attaches_the_html_alternative():
    send_templated_mail(
        "password_reset", subject="Reset", to=["a@example.com"], context=CONTEXT
    )
    message = mail.outbox[-1]
    assert message.subject == "Reset"
    assert message.alternatives[0][1] == "text/html"


def test_pt_br_translation_of_the_template():
    from django.utils import translation

    with translation.override("pt-br"):
        text, _html = render_mail("login_2fa", CONTEXT)
    assert "Código" in text
