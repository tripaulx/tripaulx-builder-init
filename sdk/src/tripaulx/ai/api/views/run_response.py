"""The HTTP answer of an enqueued run.

Immediate backend: the task ends inside the request and the answer is 200
with the result (also on a provider refusal, ``ok:false``). Queue backend:
202 with a receipt, and the client polls ``executions/<task_id>/``.
"""

from __future__ import annotations

import logging
from typing import Any

from django.tasks import TaskResultStatus
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response

from tripaulx.ai.providers.errors import make

logger = logging.getLogger("tripaulx.ai")


def failed_task_body(agent: Any, result: Any) -> dict[str, Any]:
    """Build the ``ok:false`` body of a task that crashed outside the runtime.

    ``execution.run`` never raises; a FAILED task broke around it (agent
    deleted meanwhile, wrong schema). The answer is still the diagnosis, in
    the same shape, never a 500.
    """
    detail = result.errors[-1].exception_class_path if result.errors else ""
    return {
        "ok": False,
        "execution_id": None,
        "agent": {
            "id": str(agent.pk),
            "name": agent.name,
            "slug": agent.slug,
            "role": agent.role,
        },
        "text": "",
        "data": None,
        "model": "",
        "latency_ms": 0,
        "tokens": {"input": 0, "output": 0, "total": 0},
        "cost_usd": None,
        "cost_unknown": False,
        "steps": [],
        "error": make("unexpected_error", detail=detail).as_dict(),
        "sources": [],
    }


def respond(agent: Any, result: Any) -> Response:
    """200 with the result (done or failed), or 202 with the queue receipt."""
    if result.status == TaskResultStatus.SUCCESSFUL:
        return Response(result.return_value)
    if result.status == TaskResultStatus.FAILED:
        logger.error("Run task of agent %s failed: %s", agent.slug, result.errors)
        return Response(failed_task_body(agent, result))
    return Response(
        {
            "task_id": result.id,
            "status": result.status,
            "poll": reverse("tpsdk_ai:execution", kwargs={"task_id": result.id}),
        },
        status=status.HTTP_202_ACCEPTED,
    )
