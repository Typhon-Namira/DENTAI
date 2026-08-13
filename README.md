# DENTAI backend

DENTAI is one shared FastAPI backend with a small control-plane database and one physically isolated PostgreSQL database per clinic. Clinical data never enters the control plane. Authenticated requests derive tenant routing from a signed token and revalidate the active clinic and user server-side.

## Local installation

Python 3.12 is required. The checked-in `uv.lock` is authoritative.

```bash
python -m pip install uv==0.12.3
uv sync --frozen                 # production dependencies
uv sync --frozen --extra dev     # development and validation tools
```

Copy `.env.example` to `.env`, generate a Fernet key, and replace development placeholders. Significant settings cover token lifetimes, database pool bounds, engine-cache capacity, X-ray limits, CORS, private storage, S3 timeouts, workers, and trusted forwarded proxies.

## Local infrastructure

```bash
docker compose config
docker compose up -d control-db clinic-a-db clinic-b-db
docker compose ps
```

Compose creates three physically separate PostgreSQL services. It does not silently seed credentials.

## Migrations

```bash
MIGRATION_PLANE=control DATABASE_URL="$CONTROL_DATABASE_URL" uv run alembic upgrade head
MIGRATION_PLANE=clinic DATABASE_URL="postgresql+asyncpg://...marstom..." uv run alembic upgrade head
MIGRATION_PLANE=clinic DATABASE_URL="postgresql+asyncpg://...demo..." uv run alembic upgrade head
uv run alembic heads
uv run alembic history
```

Alembic is authoritative. The onboarding command runs tenant migrations but assumes the control-plane migration has already run.

## Clinic onboarding

```bash
DATABASE_URL="postgresql+asyncpg://...clinic..." \
CONTROL_DATABASE_URL="postgresql+asyncpg://...control..." \
TENANT_DSN_ENCRYPTION_KEY="..." \
uv run python -m scripts.onboard_clinic \
  --slug marstom --name "Marstom Clinic" --branch-name Main --branch-code MAIN \
  --username director --email director@example.com --password "<secure input>" \
  --first-name Demo --last-name Director --origin http://localhost:3000
```

Repeat against a different clinic database for Demo Dental Clinic. Never commit bootstrap passwords.

## Run and validate

```bash
uv run uvicorn app.main:app --reload
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest --cov=app --cov-report=term-missing
uv run bandit -r app scripts -q
uv run pip-audit
```

Health, readiness, Swagger, and OpenAPI are at `/health`, `/ready`, `/docs`, and `/openapi.json`. Application routes use `/api/v1` and include authentication, scoped user creation, branches, patients, assignments, visits, X-rays, mock AI/review, Future Risk/Care, follow-ups, packages, usage, audit, and role dashboards.

## OPG intelligence

`AI_PROVIDER=mock` preserves deterministic development/test behavior. Production validation requires `AI_PROVIDER=real_opg`. The real path performs local protected-byte quality analysis and loads only license-guarded registered model artifacts. Since no reviewed clinical checkpoint is committed, all vision components currently report `MODEL_REQUIRED` and generate no findings. Real OPG requests return HTTP 202 and remain `QUEUED` for an isolated worker to claim with row locking, heartbeat recovery, and bounded retries. Groq is optional and receives structured JSON only; raw OPG bytes are never sent, and Groq failure cannot fail or alter vision output.

```bash
uv run python -m ai_engine.training.train --task synthetic_cpu_smoke \
  --config configs/ai/synthetic_smoke.yaml --output-dir training_artifacts/smoke
```

That command validates CPU/reproducibility plumbing with synthetic arrays only; it does not train a dental model. See `docs/AI_ARCHITECTURE.md`, `docs/AI_DATA_LICENSE_REGISTRY.md`, and model cards for the capability boundary.

Before enabling any model, run `uv run python scripts/validate_ai_release.py`. The fail-closed gate requires a matching artifact SHA-256, production-approved and checksummed datasets, validation and calibration evidence, thresholds, ONNX parity evidence, a model card, and clinical approval. It intentionally fails with `NO_PRODUCTION_MODEL` today.

## Docker and production

```bash
docker build -t dentai-backend .
docker compose up -d --build
```

The image runs as a non-root user, installs the frozen production dependency graph, and launches Uvicorn without reload. Railway deployment, migration sequencing, proxy assumptions, rollback, and object storage are documented in `docs/DEPLOYMENT_RAILWAY.md`; backup boundaries are in `docs/BACKUP_RESTORE.md`.

Frontends must call this API only. They supply a clinic slug at login but must never receive PostgreSQL credentials or control authorization through role/clinic fields.
