"""``{{ key }}`` placeholders and the legal_check command."""

from io import StringIO

from django.core.management import CommandError, call_command
from django.test import override_settings
from django.utils import translation
import pytest

from tripaulx.legal.services import fill, get_document, render_document, unfilled

TEMPLATE_KEYS = (
    "company_id",
    "company_address",
    "contact_email",
    "security_email",
    "security_owner",
    "dpo_name",
    "dpo_email",
    "jurisdiction",
    "data_location",
    "effective_date",
)
FULL_CONTEXT = dict.fromkeys(TEMPLATE_KEYS, "x")


def legal(**options):
    return override_settings(TRIPAULX={"APP_NAME": "Acme", **options})


def test_known_keys_are_filled_unknown_left_visible():
    with legal(LEGAL_CONTEXT={"company": "Acme Ltda", "dpo_email": ""}):
        text = fill("{{ company }} / {{company}} / {{ dpo_email }} / {{ other }}")
        assert text == "Acme Ltda / Acme Ltda / {{ dpo_email }} / {{ other }}"
        assert unfilled("{{ other }} {{ dpo_email }} {{ company }}") == [
            "dpo_email",
            "other",
        ]


def test_company_and_product_fall_back_to_app_name():
    with legal():
        assert fill("{{ company }} - {{ product }}") == "Acme - Acme"


def test_rendered_document_uses_the_context():
    context = {"company": "Acme Ltda", "jurisdiction": "Example State"}
    with legal(LEGAL_CONTEXT=context), translation.override("en"):
        html = render_document(get_document("terms-of-use"))
    assert "Acme Ltda" in html
    assert "laws of Example State" in html
    assert '<span class="legal-placeholder">{{ effective_date }}</span>' in html


def test_legal_check_reports_missing_keys():
    out = StringIO()
    with legal(), pytest.raises(CommandError):
        call_command("legal_check", language=["en"], stdout=out)
    report = out.getvalue()
    assert "terms-of-use: missing" in report
    assert "dpo_email" in report
    assert "incident-record-template: ok" in report


def test_legal_check_passes_with_a_full_context():
    out = StringIO()
    with legal(LEGAL_CONTEXT=FULL_CONTEXT):
        call_command("legal_check", language=["en", "pt-br"], stdout=out)
    assert "Every legal document is complete." in out.getvalue()
