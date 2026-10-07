"""The AI admin lives in workspace schemas only (its tables are not public)."""

from __future__ import annotations

from django.contrib.admin.sites import site
from django.db import connection
from django.test import RequestFactory

from tripaulx.ai.models import Agent, AIEvent, AISettings

from .helpers import AITestCase


class _Superuser:
    is_active = is_staff = is_superuser = True
    is_authenticated = True

    def has_perm(self, *_args, **_kwargs) -> bool:
        return True

    def has_module_perms(self, *_args, **_kwargs) -> bool:
        return True


def _request():
    request = RequestFactory().get("/admin/")
    request.user = _Superuser()
    return request


class AdminScopeTests(AITestCase):
    def test_visible_in_a_workspace(self):
        settings_admin = site._registry[AISettings]
        assert settings_admin.has_module_permission(_request())
        assert settings_admin.has_add_permission(_request()) is (
            not AISettings.objects.exists()
        )

    def test_absent_from_the_public_admin_without_querying(self):
        tenant = connection.tenant
        connection.set_schema_to_public()
        try:
            with self.assertNumQueries(0):
                for model in (AISettings, Agent, AIEvent):
                    model_admin = site._registry[model]
                    assert not model_admin.has_module_permission(_request())
                    assert not model_admin.has_add_permission(_request())
                    assert not model_admin.has_view_permission(_request())
            labels = {app["app_label"] for app in site.get_app_list(_request())}
            assert "tpsdk_ai" not in labels
        finally:
            connection.set_tenant(tenant)
