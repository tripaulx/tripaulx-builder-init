from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
import pytest

from tripaulx.tenants.models import Domain, Workspace
from tripaulx.tenants.services.bootstrap import ensure_domain, ensure_public

pytestmark = pytest.mark.django_db


def _run(*args: str) -> str:
    out = StringIO()
    call_command("bootstrap_workspace", *args, stdout=out)
    return out.getvalue()


def test_public_only_is_idempotent(public_schema):
    first = _run()
    second = _run()
    assert "public schema: created" in first
    assert "public schema: already existed" in second
    hosts = set(Domain.objects.values_list("domain", flat=True))
    assert hosts == {"sdk.test", "www.sdk.test"}


def test_domain_is_never_stolen(public_schema):
    public, _ = ensure_public()
    other = Workspace(schema_name="other", name="Other")
    Workspace.objects.bulk_create([other])
    other = Workspace.objects.get(schema_name="other")
    Domain.objects.create(domain="shared.sdk.test", tenant=other, is_primary=True)
    result = ensure_domain("shared.sdk.test", public, primary=False)
    assert result.conflict is True
    assert Domain.objects.get(domain="shared.sdk.test").tenant == other


def test_invalid_schema_is_rejected(public_schema):
    with pytest.raises((ValidationError, CommandError)):
        _run("--schema", "www")
