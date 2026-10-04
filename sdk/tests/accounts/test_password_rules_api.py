"""``GET /api/auth/password/rules/`` lists the rules, translated, to anyone."""

from django.utils import translation

from tripaulx.core.testing import TenantAPITestCase

RULES = "/api/auth/password/rules/"


class PasswordRulesTests(TenantAPITestCase):
    def test_anyone_gets_the_rules(self):
        resp = self.anon_api_client().get(RULES)
        assert resp.status_code == 200
        assert len(resp.data["rules"]) == 4

    def test_rules_follow_the_request_language(self):
        client = self.anon_api_client()
        english = client.get(RULES, HTTP_ACCEPT_LANGUAGE="en").data["rules"]
        with translation.override("pt-br"):
            portuguese = client.get(RULES, HTTP_ACCEPT_LANGUAGE="pt-br").data["rules"]
        assert english != portuguese

    def test_a_stale_token_is_ignored(self):
        client = self.anon_api_client()
        client.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")
        assert client.get(RULES).status_code == 200
