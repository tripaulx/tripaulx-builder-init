"""Invitations: admins invite, list and revoke; the invitee accepts once."""

from datetime import timedelta
import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone

from tripaulx.accounts.models import Invitation, Role

from .helpers import AccountsTestCase

INVITATIONS = "/api/workspace/invitations/"
ACCEPT = "/api/auth/invitations/accept/"
PASSWORD = "brand-new-password-55"


class InvitationTests(AccountsTestCase):
    def setUp(self):
        self.owner = self.verified_user("owner@example.com", role=Role.OWNER)
        self.admin = self.verified_user("admin@example.com", role=Role.ADMIN)

    def _invite(self, actor=None, email="new@example.com", role="member"):
        return self.api_client(actor or self.admin).post(
            INVITATIONS, {"email": email, "role": role}, format="json"
        )

    def _token(self):
        match = re.search(r"token=([\w-]+)", mail.outbox[-1].body)
        assert match is not None
        return match.group(1)

    def _accept(self, token, password=PASSWORD):
        body = {
            "token": token,
            "password": password,
            "password_confirm": password,
            "first_name": "New",
        }
        return self.anon_api_client().post(ACCEPT, body, format="json")

    def test_invite_sends_a_link_built_from_the_request_host(self):
        resp = self._invite()
        assert resp.status_code == 201
        assert resp.data["is_pending"] is True
        assert resp.data["invited_by"] == "admin@example.com"
        domain = self.tenant.get_primary_domain().domain
        assert f"http://{domain}/accept-invitation?token=" in mail.outbox[-1].body
        assert "Test workspace" in mail.outbox[-1].body
        assert mail.outbox[-1].to == ["new@example.com"]
        invitation = Invitation.objects.get()
        assert self._token() not in invitation.token_hash

    def test_accept_creates_a_verified_user_with_the_role(self):
        self._invite(role="admin")
        resp = self._accept(self._token())
        assert resp.status_code == 201
        assert "access" in resp.data
        user = get_user_model().objects.get(email="new@example.com")
        assert user.email_verified and user.role == Role.ADMIN
        assert user.first_name == "New"
        assert self._accept(self._token()).status_code == 400

    def test_weak_password_keeps_the_invitation(self):
        self._invite()
        token = self._token()
        assert self._accept(token, password="123").status_code == 400
        assert self._accept(token).status_code == 201

    def test_expired_or_revoked_invitations_fail(self):
        self._invite()
        token = self._token()
        Invitation.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        assert self._accept(token).status_code == 400
        self._invite(email="other@example.com")
        invitation = Invitation.objects.get(email="other@example.com")
        client = self.api_client(self.admin)
        assert client.delete(f"{INVITATIONS}{invitation.pk}/").status_code == 204
        assert self._accept(self._token()).status_code == 400

    def test_reinvite_replaces_the_previous_link(self):
        self._invite()
        first = self._token()
        self._invite()
        assert self._accept(first).status_code == 400
        assert self._accept(self._token()).status_code == 201

    def test_list_shows_pending_invitations(self):
        self._invite()
        listed = self.api_client(self.owner).get(INVITATIONS).data["results"]
        assert [i["email"] for i in listed] == ["new@example.com"]

    def test_rules(self):
        assert self._invite(email="admin@example.com").status_code == 400
        assert self._invite(role="owner").status_code == 403
        assert self._invite(actor=self.owner, role="owner").status_code == 201
        member = self.verified_user("member@example.com")
        assert self._invite(actor=member).status_code == 403
        assert self._accept("forged").status_code == 400
