from tripaulx.settings import apps, security
from tripaulx.settings.middleware import middleware


def test_project_user_app_lands_in_both_lists():
    shared = apps.shared_apps("users")
    tenant = apps.tenant_apps("users", "billing")
    assert shared[0] == "django_tenants"
    assert "users" in shared and "users" in tenant
    installed = apps.installed_apps(shared, tenant)
    assert installed[: len(shared)] == list(shared)
    assert installed.count("users") == 1
    assert installed[-1] == "billing"


def test_tenant_middleware_runs_first():
    pipeline = middleware("x.Last", after_security=("x.Early",))
    assert pipeline[0] == "tripaulx.core.middleware.TenantMiddleware"
    security_at = pipeline.index("django.middleware.security.SecurityMiddleware")
    assert pipeline[security_at + 1] == "x.Early"
    assert pipeline[-1] == "x.Last"


def test_allowed_hosts_cover_subdomains():
    assert security.allowed_hosts("example.com", "10.0.0.1") == [
        ".example.com",
        "10.0.0.1",
    ]


def test_https_origins_maps_wildcards():
    origins = security.https_origins([".example.com", "api.x.io", "*", ""])
    assert origins == ["https://*.example.com", "https://api.x.io"]
