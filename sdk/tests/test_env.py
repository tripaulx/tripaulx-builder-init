from pathlib import Path

import pytest

from tripaulx.settings import env


def test_env_file_for_known_environments():
    assert env.env_file_for("config.settings.local") == ".env.local"
    assert env.env_file_for("config.settings.prod") == ".env.prod"
    assert env.env_file_for("config.settings.test") == ".env.test"
    assert env.env_file_for("config.settings.other") == ".env"


def test_load_environment_never_overrides_process(tmp_path: Path, monkeypatch):
    (tmp_path / ".env.local").write_text("TPX_A=file-local\nTPX_B=file-local\n")
    (tmp_path / ".env").write_text("TPX_B=file-generic\nTPX_C=file-generic\n")
    monkeypatch.setenv("TPX_A", "process")
    monkeypatch.delenv("TPX_B", raising=False)
    monkeypatch.delenv("TPX_C", raising=False)
    env.load_environment(tmp_path, "config.settings.local")
    assert env.get_env("TPX_A") == "process"
    assert env.get_env("TPX_B") == "file-local"
    assert env.get_env("TPX_C") == "file-generic"
    for key in ("TPX_B", "TPX_C"):
        monkeypatch.delenv(key)


def test_required_variable_fails_fast(monkeypatch):
    monkeypatch.delenv("TPX_MISSING", raising=False)
    with pytest.raises(ValueError, match="TPX_MISSING"):
        env.get_env("TPX_MISSING", required=True)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", True), ("yes", True), ("ON", True), ("0", False), ("", True)],
)
def test_get_env_bool(monkeypatch, raw, expected):
    monkeypatch.setenv("TPX_BOOL", raw)
    assert env.get_env_bool("TPX_BOOL", default=True) is expected


def test_get_env_int_and_list(monkeypatch):
    monkeypatch.setenv("TPX_INT", "nope")
    monkeypatch.setenv("TPX_LIST", " a, ,b ,")
    assert env.get_env_int("TPX_INT", 7) == 7
    assert env.get_env_list("TPX_LIST") == ["a", "b"]


def test_database_config_defaults(monkeypatch):
    for key in ("DB_ENGINE", "DB_NAME", "DB_USER", "DB_SSLMODE"):
        monkeypatch.delenv(f"X{key}", raising=False)
    config = env.get_database_config("XDB", default_name="proj")
    assert config["ENGINE"] == "django_tenants.postgresql_backend"
    assert config["NAME"] == config["USER"] == "proj"
    assert config["OPTIONS"] == {}
