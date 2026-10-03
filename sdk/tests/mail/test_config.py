"""MailgunConfig: encrypted key, public-schema singleton and admin form."""

from django.db import connection

from tripaulx.core.testing import TenantTestCase
from tripaulx.mail.admin import MailgunConfigForm
from tripaulx.mail.models import MailgunConfig


class MailgunConfigTests(TenantTestCase):
    def test_key_is_stored_encrypted(self):
        config = MailgunConfig.load()
        config.api_key = "key-secret"
        config.save()
        stored = MailgunConfig.load()
        assert "key-secret" not in stored.api_key_encrypted
        assert stored.api_key == "key-secret"

    def test_singleton_lives_in_public_even_from_a_tenant(self):
        assert connection.schema_name == self.tenant.schema_name
        first = MailgunConfig.load()
        second = MailgunConfig.load()
        assert first.pk == second.pk == 1
        assert connection.schema_name == self.tenant.schema_name

    def test_ready_needs_enabled_key_and_domain(self):
        config = MailgunConfig(enabled=True, domain="mg.example.com")
        assert not config.is_ready
        config.api_key = "key"
        assert config.is_ready
        config.enabled = False
        assert not config.is_ready

    def test_region_selects_the_endpoint(self):
        assert MailgunConfig(region="us").base_url == "https://api.mailgun.net/v3"
        assert MailgunConfig(region="eu").base_url == "https://api.eu.mailgun.net/v3"

    def test_admin_form_saves_new_key_and_keeps_blank(self):
        data = {"enabled": True, "domain": "mg.example.com", "region": "eu"}
        form = MailgunConfigForm(data={**data, "new_api_key": "key-1"})
        assert form.is_valid(), form.errors
        saved = form.save()
        assert saved.api_key == "key-1"
        form = MailgunConfigForm(data=data, instance=MailgunConfig.load())
        assert form.is_valid()
        assert form.save().api_key == "key-1"
