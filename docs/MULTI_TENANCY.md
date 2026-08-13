# Multi-tenancy

Provision one PostgreSQL database per clinic. Run the clinic migration set against every clinic database; run control migrations only against the control database. Register encrypted async SQLAlchemy DSNs in `clinic_registry`. Never put clinical tables in the control database and never accept a request `clinic_id` as a routing authority.

```powershell
$env:MIGRATION_PLANE='control'; $env:DATABASE_URL=$env:CONTROL_DATABASE_URL; alembic upgrade head
$env:MIGRATION_PLANE='clinic'; $env:DATABASE_URL='postgresql+asyncpg://...clinic...'; alembic upgrade head
```

