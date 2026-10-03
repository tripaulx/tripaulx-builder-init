"""Access refresh has its own throttle bucket, not the shared "anon" one."""

from django.core.cache import cache
from django.utils import timezone

from tripaulx.accounts.api.views import TokenRefreshView
from tripaulx.accounts.services.tokens import refresh_for

from .helpers import REFRESH, AccountsTestCase


class RefreshThrottleTests(AccountsTestCase):
    def setUp(self):
        self.user = self.make_user()

    def _refresh(self):
        body = {"refresh": str(refresh_for(self.user))}
        return self.anon_api_client().post(REFRESH, body, format="json")

    def test_refresh_returns_a_new_access(self):
        resp = self._refresh()
        assert resp.status_code == 200
        assert "access" in resp.data

    def test_uses_its_own_scope(self):
        assert TokenRefreshView.throttle_scope == "auth_refresh"

    def test_exhausted_anon_bucket_does_not_block_refresh(self):
        now = timezone.now().timestamp()
        cache.set("throttle_anon_127.0.0.1", [now] * 100, 3600)
        assert self._refresh().status_code == 200

    def test_own_bucket_still_limits_abuse(self):
        now = timezone.now().timestamp()
        cache.set("throttle_auth_refresh_127.0.0.1", [now] * 60, 3600)
        assert self._refresh().status_code == 429
