"""Table styling hooks: IDs, severity badges and scores."""

from django.test import SimpleTestCase, override_settings

from tripaulx.legal.services import render_markdown

PT_TABLE = (
    "| ID | Classificação | Pontuação |\n"
    "|---|---|---:|\n"
    "| R-01 | Crítico | 15 |\n"
    "| R-02 | Moderado | 5 |"
)


class TableHookTests(SimpleTestCase):
    def test_table_gets_layout_for_ids_and_risk_badges(self):
        html = render_markdown(PT_TABLE)

        assert 'class="legal-table-wrap"' in html
        assert "legal-table--has-ids" in html
        assert 'class="legal-id">R-01' in html
        assert 'legal-badge-critical">Crítico' in html
        assert 'legal-badge-medium">Moderado' in html
        assert 'class="legal-score">15' in html

    def test_english_words_and_score_columns(self):
        html = render_markdown(
            "| ID | Rating | Likelihood |\n|---|---|---|\n"
            "| R-1 | High | 4 |\n| R-2 | Low | 2 |"
        )
        assert 'legal-badge-high">High' in html
        assert 'legal-badge-low">Low' in html
        assert 'class="legal-score">4' in html

    def test_plain_table_has_no_hooks(self):
        html = render_markdown("| Name | Note |\n|---|---|\n| a | b |")
        assert "legal-table--has-ids" not in html
        assert "legal-badge" not in html
        assert "legal-score" not in html

    def test_badge_words_are_configurable(self):
        words = {"critical": ("blocker",), "low": ("trivial",)}
        with override_settings(TRIPAULX={"LEGAL_BADGE_WORDS": words}):
            html = render_markdown(
                "| Item | Severity |\n|---|---|\n"
                "| a | Blocker |\n| b | Trivial |\n| c | High |"
            )
        assert 'legal-badge-critical">Blocker' in html
        assert 'legal-badge-low">Trivial' in html
        assert "legal-badge-high" not in html

    def test_cell_markup_is_still_sanitized(self):
        html = render_markdown(
            "| ID | Note |\n|---|---|\n| R-1 | [x](javascript:alert(1)) **b** |"
        )
        assert "javascript" not in html
        assert "<strong>b</strong>" in html
