"""Background tasks backend (``django.tasks``).

Django ships the task interface (``@task``, ``enqueue()``, ``TaskResult``) and
an immediate backend that runs each task in-process, right away. The database
backend comes from ``django-tasks-db``: tasks become rows in a table of the
public schema and a ``manage.py db_worker`` process (the worker app on
CapRover, ``APP_ROLE=worker``) consumes them.

``DJANGO_TASKS_BACKEND`` accepts the aliases ``immediate`` (default) and
``database``, or a full class path. The web and worker apps need the same
value: with ``database`` on the web app and no worker running, tasks stay
queued forever; the worker refuses to start with anything but ``database``.
"""

from .common import get_env

__all__ = ["TASKS"]

TASK_BACKENDS = {
    "immediate": "django.tasks.backends.immediate.ImmediateBackend",
    "database": "django_tasks_db.backend.DatabaseBackend",
}


def task_backend(value: str | None) -> str:
    """Resolve an alias (``immediate``/``database``) or return the class path.

    Stray spaces and a trailing dot (``"database."``) are tolerated: that is
    the typical slip when pasting into the CapRover dashboard.
    """
    key = (value or "").strip().strip(".").strip()
    return TASK_BACKENDS.get(key.lower(), key or TASK_BACKENDS["immediate"])


TASKS = {
    "default": {
        "BACKEND": task_backend(get_env("DJANGO_TASKS_BACKEND", "immediate")),
    }
}
