"""Create verified pre-migration backups for the control and active tenant databases."""

import asyncio
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import URL, make_url

from app.clinic_resolution.service import resolver
from app.database.control_models import ClinicRegistry
from app.database.sessions import ControlSession


def _safe_name(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in "-_" else "_" for character in value
    )


def _postgres_url(url: URL) -> URL:
    driver = url.drivername.split("+", 1)[0]
    return url.set(drivername=driver, password=None)


def backup_database(label: str, database_url: str, destination: Path) -> dict[str, object]:
    parsed = make_url(database_url)
    output = destination / f"{_safe_name(label)}.dump"
    if parsed.drivername.startswith("postgresql"):
        pg_dump = shutil.which("pg_dump")
        pg_restore = shutil.which("pg_restore")
        if not pg_dump or not pg_restore:
            raise RuntimeError("pg_dump is required for PostgreSQL backups")
        environment = os.environ.copy()
        if parsed.password:
            environment["PGPASSWORD"] = parsed.password
        subprocess.run(
            [
                pg_dump,
                "--format=custom",
                "--no-owner",
                "--no-acl",
                "--file",
                str(output),
                _postgres_url(parsed).render_as_string(hide_password=True),
            ],
            check=True,
            env=environment,
        )  # nosec B603
        subprocess.run(  # nosec B603
            [pg_restore, "--list", str(output)], check=True, stdout=subprocess.DEVNULL
        )
    elif parsed.drivername.startswith("sqlite"):
        source = Path(parsed.database or "")
        if not source.is_absolute():
            source = Path.cwd() / source
        if not source.is_file():
            raise RuntimeError(f"SQLite database does not exist for {label}")
        output = output.with_suffix(".sqlite3")
        shutil.copy2(source, output)
    else:
        raise RuntimeError(f"Unsupported database driver for {label}: {parsed.drivername}")
    if output.stat().st_size == 0:
        raise RuntimeError(f"Backup is empty for {label}")
    return {
        "label": label,
        "file": output.name,
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


async def tenant_urls() -> list[tuple[str, str]]:
    async with ControlSession() as session:
        rows = (
            await session.scalars(select(ClinicRegistry).where(ClinicRegistry.is_active.is_(True)))
        ).all()
        return [(row.slug, resolver._decrypt(row.encrypted_database_url)) for row in rows]


def main() -> None:
    destination = Path(os.environ["BACKUP_DESTINATION"])
    destination.mkdir(parents=True, exist_ok=False)
    os.chmod(destination, 0o700)
    entries = [backup_database("control", os.environ["CONTROL_DATABASE_URL"], destination)]
    for slug, database_url in asyncio.run(tenant_urls()):
        entries.append(backup_database(f"tenant-{slug}", database_url, destination))
    manifest = destination / "manifest.json"
    manifest.write_text(json.dumps({"databases": entries}, indent=2) + "\n", encoding="utf-8")
    os.chmod(destination, 0o600)
    print(f"Created and verified {len(entries)} database backups", flush=True)


if __name__ == "__main__":
    main()
