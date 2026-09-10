import hashlib
import sqlite3
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
