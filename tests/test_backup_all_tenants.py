import hashlib
import sqlite3
import subprocess
from pathlib import Path

import pytest

from scripts.backup_all_tenants import backup_database


def test_backup_database_copies_sqlite_and_records_checksum(tmp_path: Path) -> None:
    source = tmp_path / "clinic.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute("create table patient (id integer primary key, name text not null)")
        connection.execute("insert into patient (name) values ('Teta2 test')")

    destination = tmp_path / "backups"
    destination.mkdir()
    result = backup_database("tenant/test", f"sqlite+aiosqlite:///{source}", destination)

    backup = destination / "tenant_test.sqlite3"
    assert backup.is_file()
    assert result == {
        "label": "tenant/test",
        "file": backup.name,
        "bytes": backup.stat().st_size,
        "sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
    }
    with sqlite3.connect(backup) as connection:
        assert connection.execute("select name from patient").fetchone() == ("Teta2 test",)


def test_backup_database_rejects_unknown_driver(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Unsupported database driver"):
        backup_database("control", "mysql://user:secret@example.test/db", tmp_path)


def test_postgres_backup_passes_password_outside_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "backups"
    destination.mkdir()
    calls: list[tuple[list[str], dict[str, str] | None]] = []

    monkeypatch.setattr(
        "scripts.backup_all_tenants.shutil.which",
        lambda executable: f"/usr/bin/{executable}",
    )

    def run(
        command: list[str],
        *,
        check: bool,
        env: dict[str, str] | None = None,
        stdout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, env))
        if command[0].endswith("pg_dump"):
            (destination / "control.dump").write_bytes(b"verified backup")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("scripts.backup_all_tenants.subprocess.run", run)

    backup_database(
        "control",
        "postgresql+asyncpg://dentai:p%40ss@postgres:5432/platform_control_db?sslmode=require",
        destination,
    )

    command, environment = calls[0]
    assert command == [
        "/usr/bin/pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "--file",
        str(destination / "control.dump"),
        "--host",
        "postgres",
        "--port",
        "5432",
        "--username",
        "dentai",
        "--dbname",
        "platform_control_db",
    ]
    assert "p@ss" not in " ".join(command)
    assert environment is not None
    assert environment["PGPASSWORD"] == "p@ss"
    assert environment["PGSSLMODE"] == "require"
