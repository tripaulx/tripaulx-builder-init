from django.contrib.auth import get_user_model

from tests.project.sample.models import Note
from tripaulx.accounts.models import Role
from tripaulx.core.testing import TenantTestCase


class BaseModelTests(TenantTestCase):
    def test_soft_delete_hides_row_and_restore_brings_it_back(self):
        note = Note.objects.create(text="hello")
        note.delete()
        assert not Note.objects.filter(pk=note.pk).exists()
        assert Note.all_objects.get(pk=note.pk).is_deleted
        note.restore()
        assert Note.objects.filter(pk=note.pk).exists()

    def test_hard_delete_removes_row(self):
        note = Note.objects.create(text="bye")
        note.delete(hard=True)
        assert not Note.all_objects.filter(pk=note.pk).exists()


class UserTests(TenantTestCase):
    def test_user_logs_in_by_email_as_member(self):
        user = self.make_user(email="Member@Example.COM")
        assert user.email == "Member@example.com"
        assert user.role == Role.MEMBER
        assert not user.is_workspace_admin

    def test_superuser_is_verified_owner(self):
        admin = get_user_model().objects.create_superuser("root@example.com", "x")
        assert admin.email_verified and admin.is_workspace_admin
        assert admin.role == Role.OWNER

    def test_tenant_client_reaches_tenant_urls(self):
        response = self.tenant_client().get("/healthz/")
        assert response.status_code == 200
