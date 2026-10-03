"""Defaults for the legal app, overridable through ``settings.TRIPAULX``.

``LEGAL_BADGE_WORDS`` maps each severity level to the words that turn a table
cell into a badge. Words are compared case- and accent-insensitively, so
``"critico"`` also matches "Crítico". Levels are checked in order: put the
most severe first.
"""

from tripaulx.core.conf import AppSettings

DEFAULT_BADGE_WORDS: dict[str, tuple[str, ...]] = {
    "critical": ("critical", "critico", "critica"),
    "high": ("high", "alto", "alta"),
    "medium": ("medium", "moderate", "medio", "media", "moderado", "moderada"),
    "low": ("low", "baixo", "baixa"),
}

# Header words of the columns whose numeric cells get the ``legal-score`` hook.
DEFAULT_SCORE_COLUMNS: tuple[str, ...] = (
    "score",
    "level",
    "inherent",
    "residual",
    "likelihood",
    "probability",
    "impact",
    "pontuacao",
    "nivel",
    "inerente",
    "probabilidade",
    "impacto",
)

app_settings = AppSettings(
    {
        # Project folders searched before the package templates, in order.
        # Each holds ``<language>/<filename>`` (e.g. ``pt_BR/privacy-policy.md``)
        # or ``<filename>`` for every language.
        "LEGAL_CONTENT_DIRS": (),
        # Values of the ``{{ key }}`` placeholders. ``company`` and ``product``
        # fall back to APP_NAME. Empty values stay visible as placeholders.
        "LEGAL_CONTEXT": {},
        # Extra documents: dicts with the ``LegalDocument`` fields. A slug
        # already in the catalog replaces that entry.
        "LEGAL_EXTRA_DOCUMENTS": (),
        # Slugs removed from the catalog (e.g. governance documents you do not
        # keep in the product).
        "LEGAL_EXCLUDED_DOCUMENTS": (),
        # Schemas where restricted documents are served. Empty: every workspace.
        "LEGAL_SCHEMAS": (),
        # Users of these exact e-mail domains read restricted documents even
        # when they are not workspace admins (e.g. ``("example.com",)``).
        "LEGAL_ALLOWED_EMAIL_DOMAINS": (),
        # ``Cache-Control: max-age`` of the public endpoints, in seconds.
        "LEGAL_PUBLIC_CACHE_SECONDS": 3600,
        "LEGAL_BADGE_WORDS": DEFAULT_BADGE_WORDS,
        "LEGAL_SCORE_COLUMNS": DEFAULT_SCORE_COLUMNS,
    }
)
