"""``executions/<task_id>/``: progress of an enqueued run.

Only meaningful with a backend that keeps results. With the immediate one,
the result was delivered in the POST and this route answers 404; clients
never call it because they never got a 202.

The queue lives in a PUBLIC-schema table shared by every workspace: only the
user who enqueued, in the same workspace, reads the result. A run without
stored content has its row deleted as soon as the final result is delivered.
"""

from __future__ import annotations

from django.db import connection
from django.tasks import TaskResultStatus
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from tripaulx.ai.tasks import run as run_tasks


class ExecutionView(APIView):
    """Status, result and error of one enqueued run."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_poll"

    @extend_schema(
        operation_id="ai_execution_retrieve",
        responses=inline_serializer(
            "AIExecution",
            {
                "task_id": serializers.CharField(),
                "status": serializers.CharField(),
                "result": serializers.JSONField(allow_null=True),
                "error": serializers.CharField(allow_null=True),
            },
        ),
    )
    def get(self, request: Request, task_id: str) -> Response:
        """Answer the same 404 for "missing", "not kept" and "not yours"."""
        result = run_tasks.get_result(task_id)
        kwargs = getattr(result, "kwargs", None) or {}
        if (
            result is None
            or kwargs.get("schema") != connection.schema_name
            or kwargs.get("user_id") != request.user.pk
        ):
            return Response(
                {
                    "detail": _(
                        "Execution not found (the task backend keeps no results)."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        done = result.status == TaskResultStatus.SUCCESSFUL
        failed = result.status == TaskResultStatus.FAILED
        body = {
            "task_id": result.id,
            "status": result.status,
            "result": result.return_value if done else None,
            "error": result.errors[-1].exception_class_path
            if (failed and result.errors)
            else None,
        }
        if (done or failed) and kwargs.get("store_content") is False:
            run_tasks.discard_result(result)
        return Response(body)
