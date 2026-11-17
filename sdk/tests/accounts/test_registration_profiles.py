"""Registration profiles: kinds of account and the extra fields of each."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
import pytest

from tripaulx.accounts.services import profiles

from .helpers import AccountsTestCase

REGISTER = "/api/auth/register/"
CONFIG = "/api/auth/config/"
BODY = {
    "email": "ana@example.com",
    "full_name": "Ana Maria Souza",
    "password": "a-strong-password-31",
    "password_confirm": "a-strong-password-31",
}
SETTINGS = {
    "APP_NAME": "Acme",
    "BASE_DOMAIN": "sdk.test",
    "REGISTRATION_ENABLED": True,
    "REGISTRATION_PROFILES": {
        "buyer": {},
        "owner": {"required": ("phone",)},
        "broker": {"required": ("phone",)},
    },
    "REGISTRATION_FIELDS": ("phone",),
    "REGISTRATION_PROFILE_FIELD": "account_type",
}


class RegistrationProfileTests(AccountsTestCase):
    tripaulx = SETTINGS

    def post(self, **override):
        body = {**BODY, **override}
        return self.anon_api_client().post(REGISTER, body, format="json")

    def test_profile_is_required_and_must_be_known(self):
        for profile in ("", "admin"):
            resp = self.post(profile=profile)
            assert resp.status_code == 400
            assert resp.data["field"] == "profile"

    def test_profile_is_stored_and_optional_field_may_be_left_out(self):
        resp = self.post(profile="buyer")
        assert resp.status_code == 201, resp.data
        assert resp.data["profile"] == "buyer"
        user = get_user_model().objects.get()
        assert (user.account_type, user.phone) == ("buyer", "")

    def test_required_field_of_the_profile(self):
        resp = self.post(profile="broker")
        assert resp.status_code == 400
        assert resp.data["field"] == "phone"
        resp = self.post(profile="broker", phone="+5571999990000")
        assert resp.status_code == 201, resp.data
        assert get_user_model().objects.get().phone == "+5571999990000"

    def test_values_are_validated_by_the_model_field(self):
        resp = self.post(profile="owner", phone="not a phone")
        assert resp.status_code == 400
        assert resp.data["field"] == "phone"
        assert not get_user_model().objects.exists()

    def test_fields_outside_the_settings_are_ignored(self):
        resp = self.post(profile="buyer", role="owner", is_staff=True)
        assert resp.status_code == 201
        user = get_user_model().objects.get()
        assert user.role == "member" and not user.is_staff

    def test_config_lists_the_profiles(self):
        data = self.anon_api_client().get(CONFIG).data
        assert data["registration_enabled"] is True
        assert data["registration_profiles"] == [
            {"key": "buyer", "required": (), "optional": ("phone",)},
            {"key": "owner", "required": ("phone",), "optional": ()},
            {"key": "broker", "required": ("phone",), "optional": ()},
        ]


@pytest.mark.parametrize("name", ["role", "is_staff", "is_superuser", "no_such_field"])
def test_protected_or_unknown_fields_are_a_configuration_error(name):
    tripaulx = {"REGISTRATION_FIELDS": (name,)}
    with override_settings(TRIPAULX=tripaulx):
        with pytest.raises(ImproperlyConfigured):
            profiles.clean_extra("", {name: "owner"})
