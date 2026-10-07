"""Members API: admins only; owners protected; one owner always left."""

from tripaulx.accounts.models import Role
from tripaulx.accounts.services.tokens import refresh_for

from .helpers import REFRESH, AccountsTestCase

MEMBERS = "/api/workspace/members/"


class MembersTestCase(AccountsTestCase):
    def setUp(self):
        self.owner = self.verified_user("owner@example.com", role=Role.OWNER)
        self.admin = self.verified_user("admin@example.com", role=Role.ADMIN)
        self.member = self.verified_user("member@example.com")

    def _url(self, user):
        return f"{MEMBERS}{user.pk}/"

    def _role(self, actor, target, role):
        return self.api_client(actor).patch(
            self._url(target), {"role": role}, format="json"
        )


class MemberAccessTests(MembersTestCase):
    def test_admin_lists_members(self):
        resp = self.api_client(self.admin).get(MEMBERS)
        assert resp.status_code == 200
        emails = [m["email"] for m in resp.data["results"]]
        assert emails == [
            "admin@example.com",
            "member@example.com",
            "owner@example.com",
        ]

    def test_member_is_forbidden(self):
        assert self.api_client(self.member).get(MEMBERS).status_code == 403

    def test_anonymous_is_refused(self):
        assert self.anon_api_client().get(MEMBERS).status_code == 401

    def test_get_one_and_unknown_is_404(self):
        client = self.api_client(self.admin)
        assert client.get(self._url(self.member)).data["role"] == "member"
        assert client.get(f"{MEMBERS}999999/").status_code == 404
        assert client.get(f"{MEMBERS}abc/").status_code == 404


class RoleChangeTests(MembersTestCase):
    def test_admin_promotes_member_to_admin(self):
        resp = self._role(self.admin, self.member, Role.ADMIN)
        assert resp.status_code == 200
        assert resp.data["role"] == "admin"

    def test_admin_cannot_demote_an_owner(self):
        assert self._role(self.admin, self.owner, Role.MEMBER).status_code == 403
        self.owner.refresh_from_db()
        assert self.owner.role == Role.OWNER

    def test_admin_cannot_grant_owner(self):
        assert self._role(self.admin, self.member, Role.OWNER).status_code == 403

    def test_owner_grants_owner(self):
        assert self._role(self.owner, self.member, Role.OWNER).status_code == 200

    def test_last_owner_cannot_be_demoted(self):
        resp = self._role(self.owner, self.owner, Role.ADMIN)
        assert resp.status_code == 400
        assert "owner" in resp.data["detail"]

    def test_owner_can_step_down_when_another_owner_exists(self):
        self._role(self.owner, self.member, Role.OWNER)
        assert self._role(self.owner, self.owner, Role.ADMIN).status_code == 200

    def test_unknown_role_is_400(self):
        assert self._role(self.owner, self.member, "boss").status_code == 400


class DeactivateTests(MembersTestCase):
    def test_admin_deactivates_member_and_ends_sessions(self):
        refresh = str(refresh_for(self.member))
        resp = self.api_client(self.admin).delete(self._url(self.member))
        assert resp.status_code == 204
        self.member.refresh_from_db()
        assert not self.member.is_active
        assert (
            self.anon_api_client().post(REFRESH, {"refresh": refresh}).status_code
            == 401
        )

    def test_admin_cannot_deactivate_owner(self):
        assert (
            self.api_client(self.admin).delete(self._url(self.owner)).status_code == 403
        )

    def test_last_owner_cannot_be_removed(self):
        assert (
            self.api_client(self.owner).delete(self._url(self.owner)).status_code == 400
        )
        self.owner.refresh_from_db()
        assert self.owner.is_active


class ReactivateTests(MembersTestCase):
    def _reactivate(self, actor, target):
        return self.api_client(actor).post(f"{self._url(target)}reactivate/")

    def test_admin_reactivates_member_with_the_same_role(self):
        self.api_client(self.admin).delete(self._url(self.member))
        resp = self._reactivate(self.admin, self.member)
        assert resp.status_code == 200
        assert resp.data["is_active"] is True
        assert resp.data["role"] == "member"
        self.member.refresh_from_db()
        assert self.member.is_active

    def test_admin_cannot_reactivate_owner(self):
        second = self.verified_user("owner2@example.com", role=Role.OWNER)
        self.api_client(self.owner).delete(self._url(second))
        assert self._reactivate(self.admin, second).status_code == 403
        assert self._reactivate(self.owner, second).status_code == 200

    def test_member_is_forbidden(self):
        assert self._reactivate(self.member, self.admin).status_code == 403

    def test_active_member_is_a_no_op(self):
        assert self._reactivate(self.admin, self.member).data["is_active"] is True
