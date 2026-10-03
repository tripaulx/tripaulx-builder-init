"""Agent runs as ``django.tasks`` tasks: immediate or queued, same code.

The task is SELF-CONTAINED: it receives only JSON values (ids, text), enters
the tenant schema explicitly (a worker in another process does not inherit
the request's ``search_path``) and returns a JSON dict, the same body the API
answers. :func:`enqueue_run` and :func:`get_result` are the two doors the
views use; tests replace both.

Runs without stored content (``store_content=False``): with a database queue
the arguments and the result sit in a public-schema row. :func:`discard_result`
deletes it once the final result is delivered.
"""

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth import get_user_model
from django.tasks import (
    DEFAULT_TASK_BACKEND_ALIAS,
    TaskResultStatus,
    default_task_backend,
    task,
    task_backends,
)
from django_tenants.utils import schema_context
from rest_framework.renderers import JSONRenderer

from tripaulx.ai.models import Agent
from tripaulx.ai.services import execution


def _as_json(data: Any) -> dict:
    """Return the body as native JSON (UUID and Decimal converted)."""
    return json.loads(JSONRenderer().render(data))


@task()
def run_agent(
    agent_id: str,
    text: str,
    *,
    schema: str,
    origin: str,
    reference: str = "",
    user_id: int | None = None,
    context: str = "",
    overlay: str = "",
    execution_id: str | None = None,
    store_content: bool = True,
) -> dict:
    """Run :func:`execution.run` inside the tenant schema; return the result."""
    from tripaulx.ai.api.serializers import RunResultSerializer

    with schema_context(schema):
        agent = Agent.objects.get(pk=agent_id)
        user = get_user_model().objects.filter(pk=user_id).first() if user_id else None
        result = execution.run(
            agent,
            text,
            origin=origin,
            reference=reference,
            user=user,
            context=context,
            overlay=overlay,
            execution_id=execution_id,
            store_content=store_content,
        )
        return _as_json(RunResultSerializer(result).data)


def enqueue_run(
    agent: Agent,
    text: str,
    *,
    schema: str,
    origin: str,
    user: Any = None,
    context: str = "",
    reference: str = "",
    overlay: str = "",
    store_content: bool = True,
) -> Any:
    """Enqueue the run; return the ``TaskResult`` (finished when immediate)."""
    kwargs: dict[str, Any] = {
        "schema": schema,
        "origin": origin,
        "user_id": getattr(user, "pk", None),
        "context": context,
    }
    if reference:
        kwargs["reference"] = reference
    if overlay:
        kwargs["overlay"] = overlay
    if not store_content:
        kwargs["store_content"] = False
    return run_agent.enqueue(str(agent.pk), text, **kwargs)


def get_result(task_id: str) -> Any:
    """Return the ``TaskResult`` of ``task_id``, or ``None`` when not kept.

    The immediate backend keeps nothing (the answer was already delivered);
    a queue backend keeps results, and that is where clients poll.
    """
    from django.tasks.exceptions import TaskResultDoesNotExist

    try:
        return default_task_backend.get_result(task_id)
    except (NotImplementedError, TaskResultDoesNotExist, ValueError):
        return None


FINISHED = (TaskResultStatus.SUCCESSFUL, TaskResultStatus.FAILED)


def discard_result(result: Any) -> None:
    """Delete the row of a FINISHED task (database queue only).

    A running row is never deleted: the worker saves its end with
    ``update_fields`` and would fail. The status filter is in the WHERE, so
    there is no race with the worker.
    """
    try:
        from django_tasks_db.backend import DatabaseBackend
        from django_tasks_db.models import DBTaskResult
    except ImportError:
        return
    if not isinstance(task_backends[DEFAULT_TASK_BACKEND_ALIAS], DatabaseBackend):
        return
    DBTaskResult.objects.filter(pk=result.id, status__in=FINISHED).delete()
