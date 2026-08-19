# DENTAI Patient Radar — Production Runbook

## Services

Patient Radar is intentionally split into three processes built from the same repository.

1. **DENTAI Web** — existing FastAPI backend/frontend.
2. **DENTAI-RADAR-WORKER** — same main Dockerfile/image, Railway Start Command: `sh scripts/start_radar_worker.sh`.
3. **DENTAI-RADAR-COLLECTOR** — custom Dockerfile `Dockerfile.radar-collector`; private/internal service preferred.

The worker is not an HTTP server. Health is represented by a tenant-scoped database heartbeat and the `/api/v1/radar/runtime`/`metrics` endpoints on DENTAI Web.

## Railway variables

Set these on **DENTAI Web** and **DENTAI-RADAR-WORKER** (shared values where appropriate):

- `APP_ENV=production`
- all existing DENTAI production database/storage/secrets
- `RADAR_ENABLED=true`
- `RADAR_SESSION_ENCRYPTION_KEY=<dedicated Fernet key>`
- `RADAR_COLLECTOR_URL=<private collector URL>`
- `RADAR_COLLECTOR_TOKEN=<long random shared service token>`
- `RADAR_WORKER_CONCURRENCY=8` (worker only; tune with database limits)
- `RADAR_LLM_ENABLED=true`
- `GROQ_API_KEY=<existing semantic provider key>`
- optional retention/ranking variables documented in `.env.example`

Set these on **DENTAI-RADAR-COLLECTOR**:

- `RADAR_COLLECTOR_TOKEN=<same shared service token>`
- `RADAR_TELEGRAM_API_ID=<Telegram application id>`
- `RADAR_TELEGRAM_API_HASH=<Telegram application hash>`
- `RADAR_META_API_VERSION=<version approved for the Meta app>`

Set these on **DENTAI Web** for Meta OAuth:

- `RADAR_META_APP_ID`
- `RADAR_META_APP_SECRET`
- `RADAR_META_REDIRECT_URI`
- `RADAR_META_API_VERSION`

The redirect URI must match the URI configured in the Meta application.

## Database migration

Run tenant migrations through `0006_radar_production` before enabling the worker. The new tenant tables are:

- `radar_connections`
- `radar_source_candidates`
- `radar_outcomes`
- `radar_runtime_state`

Do not make the worker the migration owner. Migrations should remain a release/pre-deploy responsibility so concurrent worker replicas cannot race schema changes.

## Authorization model

### Meta

DENTAI uses OAuth/access tokens and Graph API reads. It does **not** store Meta passwords and does not automate browser login, CAPTCHA, or anti-bot challenges. The actual Facebook Pages / Instagram professional-account content available to Radar is constrained by the permissions granted to the Meta app, app review, token type, account ownership and Meta platform policy.

### Telegram

Telegram user authorization is performed by the collector via MTProto. DENTAI stores only an encrypted serialized session after the user enters the login code and, if enabled, the 2FA password. The password itself is never retained after authorization.

## High-volume funnel

Every poll follows:

`collect -> in-memory dedupe -> database dedupe -> deterministic multilingual analysis -> semantic candidate selection -> batched semantic refinement -> deterministic score -> opportunity`

This prevents already-seen and clearly irrelevant text from consuming paid semantic calls.

## Autonomous source graph

Links discovered from monitored public sources are normalized and deduplicated into `radar_source_candidates`. Repeated discovery, Armenian-market evidence and parent-source quality increase candidate score. Candidates over `RADAR_DISCOVERY_AUTO_PROMOTE_SCORE` are registered automatically and enter adaptive monitoring.

Meta sources still require API authorization/permissions before they can be collected.

## Dynamic ranking

After each successful poll, source ranking is recalculated from recent observed candidate yield, location match and activity rather than relying indefinitely on frontend seed values.

## Worker resilience

- bounded global claim batch (`RADAR_WORKER_CONCURRENCY`)
- PostgreSQL `FOR UPDATE SKIP LOCKED` claim isolation
- per-source retry/backoff in service layer
- task failure isolation through `asyncio.gather(..., return_exceptions=True)`
- periodic worker heartbeat
- periodic retention cleanup
- source-level runtime/error state retained for dashboard/observability

Multiple worker replicas are safe because source claims are database locked.

## Privacy lifecycle

- platform passwords are never stored
- authorization material is encrypted with a dedicated Fernet key
- disconnect wipes encrypted authorization material
- non-candidate raw signals are deleted after `RADAR_IGNORED_RETENTION_DAYS`
- all raw signals are deleted after `RADAR_SIGNAL_RETENTION_DAYS`
- aggregate opportunity/outcome records can remain for ranking/calibration without retaining old raw text
- author identifiers are converted to clinic/platform-scoped fingerprints in opportunity persistence

## Calibration

Radar score remains a ranking score, not a conversion probability. Clinic outcomes can be recorded as `CONTACTED`, `QUALIFIED`, `BOOKED`, `REJECTED`, or `NO_RESPONSE`. `/api/v1/radar/calibration` reports observed outcome rates by score band and only marks the data ready for recalibration after a minimum sample is available. No fabricated probability is introduced before real outcomes exist.

## Go-live validation

Before enabling automatic monitoring for a clinic:

1. migrate tenant database through `0006_radar_production`;
2. verify Web `/ready`;
3. verify collector `/health` using the internal bearer token;
4. connect Telegram and/or Meta from the Radar connection lifecycle;
5. add one source per enabled platform;
6. run each source once manually and verify `Source -> Signal -> Classification -> Opportunity -> Dashboard`;
7. start `DENTAI-RADAR-WORKER` and confirm heartbeat/source `last_success_at` advances;
8. verify `/api/v1/radar/metrics` and `/api/v1/radar/calibration`;
9. only then raise concurrency or auto-promotion thresholds.

Live Instagram/Facebook coverage cannot exceed the content that the configured Meta application is authorized to read. Live authenticated E2E therefore requires the production app credentials and approved permissions; CI uses deterministic/contract tests instead of secrets.
