import pytest

from config.settings.base_parts.tasks import TASK_BACKENDS, task_backend

DATABASE = TASK_BACKENDS["database"]
IMMEDIATE = TASK_BACKENDS["immediate"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("database", DATABASE),
        ("Database", DATABASE),
        (" database. ", DATABASE),
        ("database..", DATABASE),
        ("immediate", IMMEDIATE),
        ("", IMMEDIATE),
        (None, IMMEDIATE),
        ("  ", IMMEDIATE),
    ],
)
def test_aliases_tolerate_stray_whitespace_and_dots(value, expected):
    assert task_backend(value) == expected


def test_full_class_path_is_kept():
    path = "acme.tasks.CustomBackend"
    assert task_backend(path) == path
