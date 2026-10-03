"""A JWT is only valid in the workspace (schema) that issued it.

The contract is proven through the payload: what the defence checks is the
claim, so a token stamped with another schema (or with no claim at all) is
exactly what a token from another workspace looks like to this request.
"""

from django.db import connection
from rest_framework_simplejwt.tokens import RefreshToken

from tripaulx.accounts.services.login import make_ticket, read_ticket
from tripaulx.accounts.services.tokens import CLAIM_SCHEMA, refresh_for

from .helpers import ME, REFRESH, AccountsTestCase


class SchemaBoundTokenTests(AccountsTestCase):
    def setUp(self):
        self.user = self.make_user()

    def _with(self, access):
        client = self.anon_api_client()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return client

    def test_issued_token_carries_the_schema(self):
        refresh = refresh_for(self.user)
        assert refresh[CLAIM_SCHEMA] == connection.schema_name
        assert refresh.access_token[CLAIM_SCHEMA] == connection.schema_name

    def test_own_token_works(self):
        resp = self._with(refresh_for(self.user).access_token).get(ME)
        assert resp.status_code == 200
        assert resp.data["email"] == self.user.email

    def test_token_of_another_schema_is_refused(self):
        access = refresh_for(self.user).access_token
        access[CLAIM_SCHEMA] = "other_workspace"
        assert self._with(access).get(ME).status_code == 401

    def test_token_without_the_claim_is_refused(self):
        access = RefreshToken.for_user(self.user).access_token
        assert self._with(access).get(ME).status_code == 401

    def test_refresh_of_another_schema_does_not_renew(self):
        refresh = refresh_for(self.user)
        refresh[CLAIM_SCHEMA] = "other_workspace"
        resp = self.anon_api_client().post(REFRESH, {"refresh": str(refresh)})
        assert resp.status_code == 401

    def test_own_refresh_renews(self):
        resp = self.anon_api_client().post(
            REFRESH, {"refresh": str(refresh_for(self.user))}
        )
        assert resp.status_code == 200
        assert "access" in resp.data

    def test_logout_blacklists_the_refresh(self):
        refresh = str(refresh_for(self.user))
        client = self.api_client(self.user)
        assert client.post("/api/auth/logout/", {"refresh": refresh}).status_code == 204
        resp = self.anon_api_client().post(REFRESH, {"refresh": refresh})
        assert resp.status_code == 401

    def test_logout_ignores_garbage(self):
        resp = self.api_client(self.user).post("/api/auth/logout/", {"refresh": "x"})
        assert resp.status_code == 204

    def test_login_ticket_is_bound_to_the_schema(self):
        ticket = make_ticket(self.user)
        assert read_ticket(ticket) == self.user
        connection.set_schema_to_public()
        try:
            assert read_ticket(ticket) is None
        finally:
            connection.set_tenant(self.tenant)
