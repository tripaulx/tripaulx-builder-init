from django.core.exceptions import ValidationError
from django.test import override_settings
import pytest

from tripaulx.tenants.models import Workspace
from tripaulx.tenants.services.slugs import is_slug_available, normalize_slug
from tripaulx.tenants.validators import validate_workspace_slug


@pytest.mark.parametrize("slug", ["acme", "acme_co", "a12", "x" * 30])
def test_valid_slugs(slug):
    validate_workspace_slug(slug)


@pytest.mark.parametrize(
    "slug", ["ab", "1acme", "Acme", "acme-co", "x" * 31, "", "www", "pg_acme"]
)
def test_invalid_or_reserved_slugs(slug):
    with pytest.raises(ValidationError):
        validate_workspace_slug(slug)


def test_project_can_reserve_more_slugs():
    with override_settings(TRIPAULX={"EXTRA_RESERVED_SLUGS": ("acme",)}):
        with pytest.raises(ValidationError):
            validate_workspace_slug("acme")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Café & Cia Comércio Ltda", "cafe_cia_comercio_ltda"),
        ("  Acme -- Co ", "acme_co"),
        ("123 Studio", "w123_studio"),
        ("", ""),
    ],
)
def test_normalize_slug(text, expected):
    assert normalize_slug(text) == expected


@pytest.mark.django_db
def test_availability_checks_existing_workspaces(public_schema):
    Workspace.objects.bulk_create([Workspace(schema_name="taken", name="Taken")])
    assert is_slug_available("taken") is False
    assert is_slug_available("free_one") is True
    assert is_slug_available("www") is False
