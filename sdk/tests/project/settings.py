"""Minimal project used by the SDK test-suite (dogfoods tripaulx.settings)."""

from __future__ import annotations

import getpass
from pathlib import Path

from tripaulx.settings import apps as sdk_apps
from tripaulx.settings.env import get_database_config, get_env
from tripaulx.settings.middleware import middleware
from tripaulx.settings.observability import logging_config

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = "sdk-tests-only"
DEBUG = False
ALLOWED_HOSTS = ["*"]

SHARED_APPS = sdk_apps.shared_apps("tests.project.users")
TENANT_APPS = sdk_apps.tenant_apps("tests.project.users", "tests.project.sample")
INSTALLED_APPS = sdk_apps.installed_apps(SHARED_APPS, TENANT_APPS)

TENANT_MODEL = sdk_apps.TENANT_MODEL
TENANT_DOMAIN_MODEL = sdk_apps.TENANT_DOMAIN_MODEL
DATABASE_ROUTERS = sdk_apps.DATABASE_ROUTERS
PUBLIC_SCHEMA_NAME = sdk_apps.PUBLIC_SCHEMA_NAME
SHOW_PUBLIC_IF_NO_TENANT_FOUND = sdk_apps.SHOW_PUBLIC_IF_NO_TENANT_FOUND

AUTH_USER_MODEL = "users.User"
MIDDLEWARE = middleware()
ROOT_URLCONF = "tests.project.urls"
PUBLIC_SCHEMA_URLCONF = "tests.project.urls_public"

_db_user = get_env("DB_USER", getpass.getuser())
DATABASES = {"default": get_database_config("DB", default_name="tripaulx_sdk")}
DATABASES["default"]["USER"] = _db_user

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

STATIC_URL = "/static/"
USE_TZ = True
LANGUAGE_CODE = "en"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
LOGGING = logging_config("WARNING")

TRIPAULX = {"BASE_DOMAIN": "sdk.test"}
