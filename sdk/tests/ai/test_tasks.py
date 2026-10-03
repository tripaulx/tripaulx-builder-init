"""Runs as ``django.tasks`` tasks: immediate today, queued with polling."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

from django.db import connection
from django.tasks import TaskResultStatus

from tripaulx.ai.tasks import run as run_tasks

from .helpers import OPENAI_SEND, AITestCase, configure_ai, new_agent, openai_response

AGENTS = "/api/v1/ai/agents/"
EXECUTIONS = "/api/v1/ai/executions/"


class ImmediateTaskTests(AITestCase):
    def setUp(self):
        super().setUp()
        configure_ai()
        self.agent = new_agent("Solo")
        self.url = f"{AGENTS}{self.agent.pk}/run/"

    def test_run_answers_200_with_the_result(self):
        with mock.patch.object(*OPENAI_SEND, return_value=openai_response("opinion")):
            r = self.member_api.post(self.url, {"input": "doc"}, format="json")
        assert r.status_code == 200 and r.data["text"] == "opinion"
        assert r.data["agent"]["slug"] == "solo" and "execution_id" in r.data

    def test_task_gets_the_schema_and_json_values_only(self):
        fake = SimpleNamespace(enqueue=mock.Mock())
        fake.enqueue.return_value = SimpleNamespace(
            id="t1",
            status=TaskResultStatus.SUCCESSFUL,
            return_value={"ok": True},
            errors=[],
        )
        with mock.patch.object(run_tasks, "run_agent", fake):
            self.member_api.post(
                self.url, {"input": "doc", "context": "c"}, format="json"
            )
        args, kwargs = fake.enqueue.call_args
        assert args == (str(self.agent.pk), "doc")
        assert kwargs["schema"] == connection.schema_name
        assert (kwargs["origin"], kwargs["context"]) == ("playground", "c")
        assert kwargs["user_id"] == self.member.pk

    def test_task_returns_native_json(self):
        with mock.patch.object(*OPENAI_SEND, return_value=openai_response()):
            result = run_tasks.run_agent.call(
                str(self.agent.pk), "doc", schema=connection.schema_name, origin="api"
            )
        assert result["ok"] and isinstance(result["execution_id"], str)
        assert isinstance(result["cost_usd"], float)

    def test_crashed_task_is_ok_false_not_500(self):
        failed = SimpleNamespace(
            id="t2",
            status=TaskResultStatus.FAILED,
            errors=[SimpleNamespace(exception_class_path="builtins.RuntimeError")],
        )
        with mock.patch.object(run_tasks, "enqueue_run", return_value=failed):
            r = self.member_api.post(self.url, {"input": "doc"}, format="json")
        assert r.status_code == 200 and not r.data["ok"]
        assert r.data["error"]["code"] == "unexpected_error"
        assert "RuntimeError" in r.data["error"]["detail"]

    def test_polling_is_404_with_the_immediate_backend(self):
        r = self.member_api.get(f"{EXECUTIONS}abc123/")
        assert r.status_code == 404 and "keeps no results" in r.data["detail"]

    def test_store_content_only_goes_when_false(self):
        fake = SimpleNamespace(enqueue=mock.Mock())
        with mock.patch.object(run_tasks, "run_agent", fake):
            run_tasks.enqueue_run(self.agent, "x", schema="s", origin="api")
            assert "store_content" not in fake.enqueue.call_args.kwargs
            run_tasks.enqueue_run(
                self.agent,
                "x",
                schema="s",
                origin="api",
                store_content=False,
                reference="invoice:1",
                overlay="rules",
            )
        kwargs = fake.enqueue.call_args.kwargs
        assert kwargs["store_content"] is False
        assert (kwargs["reference"], kwargs["overlay"]) == ("invoice:1", "rules")


class QueuedTaskTests(AITestCase):
    def setUp(self):
        super().setUp()
        configure_ai()
        self.agent = new_agent("Solo")

    def _result(self, status, **fields):
        kwargs = {"schema": connection.schema_name, "user_id": self.member.pk}
        kwargs.update(fields.pop("kwargs", {}))
        fields.setdefault("errors", [])
        return SimpleNamespace(id="abc123", status=status, kwargs=kwargs, **fields)

    def test_post_answers_202_with_a_receipt(self):
        pending = self._result(TaskResultStatus.READY)
        with mock.patch.object(run_tasks, "enqueue_run", return_value=pending):
            r = self.member_api.post(
                f"{AGENTS}{self.agent.pk}/run/", {"input": "doc"}, format="json"
            )
        assert r.status_code == 202
        assert r.data == {
            "task_id": "abc123",
            "status": "READY",
            "poll": "/api/v1/ai/executions/abc123/",
        }

    def test_polling_returns_progress_result_and_error(self):
        cases = [
            (self._result(TaskResultStatus.RUNNING), "RUNNING", None),
            (
                self._result(TaskResultStatus.SUCCESSFUL, return_value={"ok": True}),
                "SUCCESSFUL",
                {"ok": True},
            ),
        ]
        for result, status, payload in cases:
            with mock.patch.object(run_tasks, "get_result", return_value=result):
                r = self.member_api.get(f"{EXECUTIONS}abc123/")
            assert r.data["status"] == status and r.data["result"] == payload
        failed = self._result(
            TaskResultStatus.FAILED,
            errors=[SimpleNamespace(exception_class_path="x.E")],
        )
        with mock.patch.object(run_tasks, "get_result", return_value=failed):
            assert self.member_api.get(f"{EXECUTIONS}abc123/").data["error"] == "x.E"

    def test_other_users_and_workspaces_get_404(self):
        for extra in ({"user_id": self.member.pk + 999}, {"schema": "other"}):
            result = self._result(
                TaskResultStatus.SUCCESSFUL, return_value={"ok": True}, kwargs=extra
            )
            with mock.patch.object(run_tasks, "get_result", return_value=result):
                r = self.member_api.get(f"{EXECUTIONS}abc123/")
            assert r.status_code == 404 and "result" not in r.data
        assert self.anon_api_client().get(f"{EXECUTIONS}abc123/").status_code == 401

    def test_contentless_result_is_discarded_once_finished(self):
        no_content = {"store_content": False}
        cases = [
            (self._result(TaskResultStatus.RUNNING, kwargs=no_content), False),
            (
                self._result(
                    TaskResultStatus.SUCCESSFUL, return_value={}, kwargs=no_content
                ),
                True,
            ),
            (self._result(TaskResultStatus.SUCCESSFUL, return_value={}), False),
        ]
        for result, discarded in cases:
            with (
                mock.patch.object(run_tasks, "get_result", return_value=result),
                mock.patch.object(run_tasks, "discard_result") as discard,
            ):
                self.member_api.get(f"{EXECUTIONS}abc123/")
            assert discard.called == discarded
