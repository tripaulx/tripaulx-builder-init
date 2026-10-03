"""The "test AI" call (``test/``): diagnosis as 200, admins only, event recorded."""

from __future__ import annotations

from unittest import mock

import anthropic
import openai

from tripaulx.ai.models import AIEvent, AIKey, AISettings
from tripaulx.ai.services import probe
from tripaulx.core import crypto

from .helpers import (
    ANTHROPIC_SEND,
    OPENAI_SEND,
    AITestCase,
    anthropic_response,
    configure_ai,
    openai_response,
    sdk_connection_error,
    sdk_error,
)

URL = "/api/v1/ai/test/"


class ProbeServiceTests(AITestCase):
    def setUp(self):
        super().setUp()
        self.settings, _ = configure_ai(
            identifier="gpt-5.6", enabled=False, key="sk-secret"
        )

    def _probe(self, **patch):
        with mock.patch.object(*OPENAI_SEND, **patch) as send:
            return probe.probe(self.settings), send

    def test_success_reports_model_and_answer(self):
        r, send = self._probe(return_value=openai_response("ok", model="gpt-5.6-sol"))
        assert r.ok and r.answer == "ok" and r.model == "gpt-5.6-sol" and r.error == ""
        api_key, params, _ = send.call_args.args
        assert api_key == "sk-secret" and "sk-secret" not in str(params)
        assert params["input"] == probe.QUESTION and params["store"] is False

    def test_refusals_become_sentences(self):
        cases = [
            (sdk_error(openai, 401, "bad key"), "rejected the API key"),
            (sdk_error(openai, 404), "gpt-5.6"),
            (sdk_error(openai, 429), "usage limit"),
            (sdk_error(openai, 503), "unavailable"),
            (sdk_connection_error(openai), "Could not reach OpenAI"),
        ]
        for exc, words in cases:
            r, _ = self._probe(side_effect=exc)
            assert not r.ok and words in r.error

    def test_records_a_test_event(self):
        self._probe(return_value=openai_response())
        ev = AIEvent.objects.get()
        assert (ev.origin, ev.operation, ev.status) == ("test", "test", "success")

    def test_header_unsafe_key_never_calls(self):
        AIKey.objects.all().delete()
        AIKey.objects.create(
            provider="openai", api_key_encrypted=crypto.encrypt("sk-aМb")
        )
        r, send = self._probe()
        send.assert_not_called()
        assert not r.ok and "U+041C" in r.error

    def test_anthropic_probe(self):
        configure_ai(
            provider="anthropic", identifier="claude-haiku-4-5-20251001", key="sk-ant"
        )
        with mock.patch.object(*ANTHROPIC_SEND, return_value=anthropic_response("ok")):
            assert probe.probe(AISettings.load()).ok
        with mock.patch.object(*ANTHROPIC_SEND, side_effect=sdk_error(anthropic, 401)):
            assert "Anthropic rejected" in probe.probe(AISettings.load()).error


class ProbeViewTests(AITestCase):
    def test_admin_only(self):
        configure_ai()
        assert self.anon_api_client().post(URL).status_code == 401
        assert self.member_api.post(URL).status_code == 403

    def test_provider_refusal_is_200_not_401(self):
        configure_ai(key="sk-never-in-answer")
        with mock.patch.object(
            *OPENAI_SEND, side_effect=sdk_error(openai, 401, "nope")
        ):
            response = self.admin_api.post(URL)
        assert response.status_code == 200 and not response.data["ok"]
        assert "sk-never-in-answer" not in str(response.content)

    def test_works_while_disabled(self):
        configure_ai(enabled=False)
        with mock.patch.object(*OPENAI_SEND, return_value=openai_response("ok")):
            assert self.admin_api.post(URL).data["ok"]

    def test_incomplete_configuration_is_400(self):
        configure_ai(key=None)
        assert self.admin_api.post(URL).status_code == 400
        configure_ai()
        settings = AISettings.load()
        settings.model_identifier = ""
        settings.save()
        assert self.admin_api.post(URL).status_code == 400
        assert self.admin_api.get(URL).status_code == 405
