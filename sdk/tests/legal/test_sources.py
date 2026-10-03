"""Where documents come from: package templates, project overrides, language."""

from importlib import resources

from django.test import override_settings
from django.utils import translation
import pytest

from tripaulx.legal.services import (
    DEFAULT_DOCUMENTS,
    DocumentUnavailable,
    LegalDocument,
    get_document,
    read_source,
    resolve,
)

LANGUAGES = ("en", "pt_BR")


def legal(**options):
    return override_settings(TRIPAULX=options)


def test_package_ships_every_template_in_both_languages():
    content = resources.files("tripaulx.legal").joinpath("content")
    for language in LANGUAGES:
        for document in DEFAULT_DOCUMENTS:
            text = content.joinpath(language, document.filename).read_text("utf-8")
            assert text.startswith("# "), (language, document.filename)


def test_active_language_picks_the_template():
    terms = get_document("terms-of-use")
    with translation.override("pt-br"):
        assert read_source(terms).startswith("# Termos de uso")
    with translation.override("en"):
        assert read_source(terms).startswith("# Terms of use")


def test_unknown_language_falls_back_to_english():
    with translation.override("de"):
        assert read_source(get_document("privacy-policy")).startswith(
            "# Privacy policy"
        )


def test_project_files_win_and_neutral_file_serves_every_language(tmp_path):
    (tmp_path / "pt_BR").mkdir()
    (tmp_path / "pt_BR" / "terms-of-use.md").write_text("# Termos da Acme")
    (tmp_path / "privacy-policy.md").write_text("# Acme privacy")
    terms, privacy = get_document("terms-of-use"), get_document("privacy-policy")
    with legal(LEGAL_CONTENT_DIRS=[str(tmp_path)]):
        assert read_source(terms, "pt-br") == "# Termos da Acme"
        # No project file in English: the package template is used.
        assert read_source(terms, "en").startswith("# Terms of use")
        assert read_source(privacy, "pt-br") == "# Acme privacy"
        assert read_source(privacy, "en") == "# Acme privacy"


def test_project_english_file_beats_package_translation(tmp_path):
    (tmp_path / "en").mkdir()
    (tmp_path / "en" / "risk-matrix.md").write_text("# Acme risks")
    with legal(LEGAL_CONTENT_DIRS=[str(tmp_path)]):
        assert read_source(get_document("risk-matrix"), "pt-br") == "# Acme risks"


def test_symlink_escaping_the_folder_is_ignored(tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("# secret")
    project = tmp_path / "legal"
    (project / "en").mkdir(parents=True)
    (project / "en" / "terms-of-use.md").symlink_to(outside)
    with legal(LEGAL_CONTENT_DIRS=[str(project)]):
        path = resolve(get_document("terms-of-use"), "en")
        assert path is not None and path != outside.resolve()
        assert read_source(get_document("terms-of-use"), "en") != "# secret"


def test_missing_file_is_unavailable(tmp_path):
    extra = {
        "slug": "cookie-policy",
        "title": "Cookies",
        "description": "",
        "filename": "cookie-policy.md",
        "category": "Policies",
    }
    with legal(LEGAL_EXTRA_DOCUMENTS=[extra], LEGAL_CONTENT_DIRS=[str(tmp_path)]):
        with pytest.raises(DocumentUnavailable):
            read_source(LegalDocument(**extra))
