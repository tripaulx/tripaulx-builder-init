"""Locate and read the Markdown source of a document.

Search order, first match wins:

1. each folder of ``LEGAL_CONTENT_DIRS``: the active language
   (``pt_BR/``, then ``pt/``), the language-neutral file at the folder root,
   then ``en/``;
2. the templates shipped in the package: the active language, then ``en/``.

So a project file always wins over a package template, even in another
language. Every candidate is resolved and must stay inside its folder.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from django.utils import translation

from ..conf import app_settings
from .catalog import LegalDocument

FALLBACK_LANGUAGE = "en"


class DocumentUnavailable(Exception):  # noqa: N818 - reads as a state
    """The document is in the catalog but its file cannot be read."""


def package_content_root() -> Path:
    """Return the folder of the templates shipped with the SDK."""
    return Path(str(resources.files("tripaulx.legal").joinpath("content")))


def language_dirs(language: str | None = None) -> list[str]:
    """Return the folder names tried for ``language`` (active one if None)."""
    code = language or translation.get_language() or FALLBACK_LANGUAGE
    locale = translation.to_locale(code)
    names = [locale, locale.split("_")[0]]
    return list(dict.fromkeys(name for name in names if name))


def _inside(root: Path, relative: str) -> Path | None:
    """Return ``root/relative`` if it is a file that stays inside ``root``."""
    base = root.resolve()
    path = (base / relative).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        return None
    return path


def candidates(
    document: LegalDocument, language: str | None = None
) -> list[tuple[Path, str]]:
    """Return ``(content folder, relative path)`` pairs in priority order."""
    langs = language_dirs(language)
    found: list[tuple[Path, str]] = []
    for folder in app_settings.LEGAL_CONTENT_DIRS:
        names = [f"{lang}/{document.filename}" for lang in langs]
        names += [document.filename, f"{FALLBACK_LANGUAGE}/{document.filename}"]
        found += [(Path(folder), name) for name in dict.fromkeys(names)]
    root = package_content_root()
    for lang in dict.fromkeys([*langs, FALLBACK_LANGUAGE]):
        found.append((root, f"{lang}/{document.filename}"))
    return found


def resolve(document: LegalDocument, language: str | None = None) -> Path | None:
    """Return the file serving ``document`` in ``language``, or None."""
    for root, relative in candidates(document, language):
        match = _inside(root, relative)
        if match is not None:
            return match
    return None


def read_source(document: LegalDocument, language: str | None = None) -> str:
    """Return the Markdown text of ``document``.

    Raises :class:`DocumentUnavailable` when no file exists or it cannot be
    read.
    """
    path = resolve(document, language)
    if path is None:
        raise DocumentUnavailable(document.slug)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DocumentUnavailable(document.slug) from exc
