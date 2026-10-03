from datetime import timedelta

from tripaulx.settings import apps
from tripaulx.settings.rest import (
    JWT_AUTHENTICATION,
    rest_framework,
    simple_jwt,
    spectacular,
)


def test_rest_framework_defaults():
    config = rest_framework()
    assert config["DEFAULT_AUTHENTICATION_CLASSES"] == [JWT_AUTHENTICATION]
    assert config["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated"
    ]
    rates = config["DEFAULT_THROTTLE_RATES"]
    expected = {"anon", "user", "auth_login", "auth_register", "auth_otp"}
    assert expected | {"auth_refresh"} == set(rates)
    assert config["DEFAULT_SCHEMA_CLASS"] == "drf_spectacular.openapi.AutoSchema"
    assert config["PAGE_SIZE"] == 20


def test_rest_framework_overrides_merge_dicts():
    config = rest_framework(DEFAULT_THROTTLE_RATES={"anon": "5/min"}, PAGE_SIZE=50)
    assert config["DEFAULT_THROTTLE_RATES"]["anon"] == "5/min"
    assert config["DEFAULT_THROTTLE_RATES"]["auth_login"] == "10/min"
    assert config["PAGE_SIZE"] == 50
    assert rest_framework()["DEFAULT_THROTTLE_RATES"]["anon"] == "100/hour"


def test_simple_jwt_lifetimes_and_rotation():
    config = simple_jwt("k" * 32)
    assert config["ACCESS_TOKEN_LIFETIME"] == timedelta(minutes=30)
    assert config["REFRESH_TOKEN_LIFETIME"] == timedelta(hours=12)
    assert config["ROTATE_REFRESH_TOKENS"] and config["BLACKLIST_AFTER_ROTATION"]
    assert config["SIGNING_KEY"] == "k" * 32
    assert "SIGNING_KEY" not in simple_jwt("")


def test_spectacular_is_admin_only():
    config = spectacular("Acme API")
    assert config["TITLE"] == "Acme API"
    assert config["SERVE_PERMISSIONS"] == ["rest_framework.permissions.IsAdminUser"]


def test_app_lists_include_api_and_mail_apps():
    shared, tenant = apps.shared_apps(), apps.tenant_apps()
    blacklist = "rest_framework_simplejwt.token_blacklist"
    assert blacklist in shared and blacklist in tenant
    assert "tripaulx.mail" in shared and "tripaulx.mail" not in tenant
    for app in ("rest_framework", "drf_spectacular", "corsheaders"):
        assert app in shared
