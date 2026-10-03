from django.utils import translation

from tripaulx.accounts.models import Role


def test_pt_br_translation_is_shipped():
    with translation.override("pt-br"):
        assert str(Role.OWNER.label) == "Proprietário"
    with translation.override("en"):
        assert str(Role.OWNER.label) == "Owner"
