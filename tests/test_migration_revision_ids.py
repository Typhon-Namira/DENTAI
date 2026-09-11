from alembic.config import Config
from alembic.script import ScriptDirectory

ALEMBIC_VERSION_NUM_MAX_LENGTH = 32


def test_all_alembic_revision_ids_fit_version_table() -> None:
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    oversized = sorted(
        revision.revision
        for revision in scripts.walk_revisions()
        if len(revision.revision) > ALEMBIC_VERSION_NUM_MAX_LENGTH
    )

    assert oversized == [], (
        "Alembic stores revision IDs in alembic_version.version_num VARCHAR(32) by default; "
        f"oversized revisions: {oversized}"
    )
