from django.utils import translation

from tripaulx.ai.catalog.models import CostTier
from tripaulx.ai.providers.errors import label, make


def test_pt_br_translation_of_errors_and_catalog():
    with translation.override("pt-br"):
        assert label("daily_cap_reached") == "Teto diário atingido"
        assert str(CostTier.ECONOMY.label) == "Econômico"
        assert "recusou a chave" in make("key_rejected", provider="OpenAI").message
    with translation.override("en"):
        assert label("daily_cap_reached") == "Daily cap reached"
