# Care API deployment

The production frontend is hosted by Vercel at `www.teta2.com`. Its same-origin `/api`, `/health`, and `/ready` rewrites currently target `https://35-159-65-156.sslip.io`, an EC2-hosted FastAPI service. The Care API must be deployed to that service before the frontend release is considered operational.

## GitHub environment secrets

Create a protected GitHub environment named `production`, require an approving reviewer, and configure:

- `EC2_HOST`: backend host name or IP.
- `EC2_USER`: restricted deployment SSH user with Docker access.
- `EC2_SSH_PRIVATE_KEY`: private key for that user.
- `EC2_KNOWN_HOSTS`: pinned `ssh-keyscan` output reviewed out of band; never disable host-key checking.
- `EC2_RELEASE_ROOT`: absolute release directory, for example `/opt/dentai/releases`.
- Runtime configuration is copied from the existing `teta2-web` container on the server; it is not recreated in GitHub.
- `CARE_BACKEND_URL`: canonical backend origin used by the Vercel rewrite.
- `CARE_FRONTEND_URL`: `https://www.teta2.com`, used to verify the proxy independently.
- `CARE_SMOKE_CLINIC_SLUG`, `CARE_SMOKE_IDENTIFIER`, `CARE_SMOKE_PASSWORD`: a dedicated Doctor smoke-test account in a non-patient production test tenant.

These values must be environment secrets on the exact environment selected when dispatching the workflow. Repository variables and secrets attached to a differently named environment are not visible to the deployment job. The workflow validates every required name before attempting SSH and reports each missing name without printing secret values.

Runtime secrets remain on EC2. The release extracts the existing `teta2-web` container environment into a mode-600 release file for migration and replacement, preserving its database, object-storage, AI, Groq, and WhatsApp configuration without copying those values to GitHub.

Set `WEB_CONCURRENCY=2` or higher for production. The startup script also defaults to two API workers so a single blocked worker cannot make authentication and health endpoints unavailable.

## Release procedure

Run the **Deploy Care API** workflow manually against the protected environment. It:

1. runs Python formatting, lint, typing, tests, frontend tests/build, and a Docker build;
2. uploads an immutable source release and builds an image tagged with the commit SHA;
3. runs `scripts/migrate_all_tenants.py`, which upgrades the control plane and every active tenant to Alembic head;
4. health-checks a loopback-only candidate, renames the existing `teta2-web` container as the rollback unit, and starts the replacement with its mounted volumes on `teta2-internal` so the existing Caddy service continues to route to it;
5. checks authenticated Care dashboard, plan, appointment, and conversation endpoints at both the backend origin and the Vercel frontend proxy;
6. restores the exact previous container, including its environment, network configuration, and volumes, if post-deployment smoke testing fails.

Database migrations are additive. Back up the control database and every tenant database before approving the production job. Application rollback does not downgrade the database; the new columns and table are backward-compatible with the preceding application release.

The active backend persists WhatsApp authentication in the named Docker volume `dentai-whatsapp-sessions`. The disposable candidate disables the embedded service so it cannot race the active instance for the same provider session. `TETA2_CARE_STATUS_CALLBACK_URL` is optional when the inbound callback ends in `/inbound`; in that case the service derives the sibling `/status` endpoint automatically.

## Vercel configuration

`frontend-test/vercel.json` contains the explicit backend origin. `VITE_DENTAI_API_BASE_URL` is honored by the client and should remain empty for the same-origin production deployment. If the backend origin changes, update the three rewrite destinations in one reviewed commit and run the authenticated smoke test against both origins.

Delete any Vercel project value such as `VITE_DENTAI_API_BASE_URL=https://api-domain` rather than substituting a placeholder. The client defensively rejects placeholder or malformed origins and uses the same-origin rewrite, and CI rejects known placeholders compiled into `dist`.
