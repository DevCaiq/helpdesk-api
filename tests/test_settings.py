import os
import subprocess
import sys


def load_settings(module, **variables):
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"SECRET_KEY", "DATABASE_URL", "DEBUG", "DJANGO_SETTINGS_MODULE"}
    }
    env.update(variables)
    return subprocess.run(
        [
            sys.executable,
            "-c",
            f"import {module} as s; print(s.DATABASES['default']['ENGINE']); print(s.DEBUG)",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_test_settings_uses_sqlite():
    result = load_settings("config.settings.test")
    assert result.returncode == 0, result.stderr
    assert "sqlite3" in result.stdout


def test_dev_uses_sqlite_even_with_production_database_url():
    result = load_settings("config.settings.dev", DATABASE_URL="postgres://u:p@localhost/db")
    assert result.returncode == 0, result.stderr
    assert "sqlite3" in result.stdout


def test_prod_requires_secret():
    result = load_settings("config.settings.prod", DATABASE_URL="postgres://u:p@localhost/db")
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr


def test_prod_rejects_sqlite():
    result = load_settings(
        "config.settings.prod", SECRET_KEY="test-secret", DATABASE_URL="sqlite:///db.sqlite3"
    )
    assert result.returncode != 0
    assert "PostgreSQL" in result.stderr


def test_prod_disables_debug():
    result = load_settings(
        "config.settings.prod",
        SECRET_KEY="test-secret",
        DATABASE_URL="postgres://u:p@localhost/db",
        DEBUG="True",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("False")
