# Railway deployment

1. Create one backend service from this repository and provision one PostgreSQL service for the control plane. Provision a separate PostgreSQL service/database and credentials for every clinic.
2. Configure every variable documented in `.env.example`. Set `APP_ENV=production`, unique random application/token secrets, a valid Fernet key, explicit frontend origins, and private S3-compatible storage. Railway's internal database URLs may need conversion to `postgresql+asyncpg://`.
3. Build from the Dockerfile. Production start command is already its image command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers ${WEB_CONCURRENCY:-1} --proxy-headers --forwarded-allow-ips=$FORWARDED_ALLOW_IPS`. Start with one worker; scale replicas based on observed load.
4. Before release, back up databases and test migrations in staging. Run control migrations with `MIGRATION_PLANE=control DATABASE_URL=$CONTROL_DATABASE_URL alembic upgrade head`. Run `MIGRATION_PLANE=clinic DATABASE_URL=<clinic-async-dsn> alembic upgrade head` independently for every clinic.
5. Run `python -m scripts.onboard_clinic ...` for a new clinic after its clinic migration. Supply bootstrap credentials through the deployment shell or a secret manager, never source control.
6. Set the Railway health-check path to `/health`. `/ready` additionally probes the control database and is appropriate for operational readiness checks.
7. Configure each clinic frontend origin in `CORS_ALLOWED_ORIGINS` and in its registry record. TLS terminates at Railway; `FORWARDED_ALLOW_IPS` must name only the trusted proxy range so forwarded HTTPS information is accepted safely.
8. Inspect JSON logs in Railway using request IDs. Logs intentionally omit tokens, database URLs, passwords, and file contents.
9. Roll back by deploying the previous compatible image. Restore databases only for destructive/data-corruption events and follow `BACKUP_RESTORE.md`; never wipe a production database to recover a failed deployment.

The repository does not deploy itself and does not claim Railway backups are enabled. Configure PostgreSQL retention, object-storage versioning, alerting, and restore drills in the chosen production accounts.
