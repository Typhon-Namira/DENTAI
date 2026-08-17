# DENTAI Internal Product Test Frontend

An isolated React + TypeScript + Vite interface for the first real end-to-end DENTAI product test. It uses the existing backend contracts and is built into the existing DENTAI production image.

## Production deployment

The frontend and FastAPI backend are served by the same existing DENTAI Railway service and public URL. There is no separate frontend service or frontend domain.

The current test environment URL is:

https://dentai-production-13d1.up.railway.app

This URL is documentation for the current environment, not a hardcoded application dependency. The same image can run under another domain.

In production:

- `/` serves the built DENTAI frontend;
- `/health` and `/ready` remain FastAPI health endpoints;
- `/api/v1/*` remains the existing FastAPI API;
- frontend API requests are same-origin;
- `VITE_DENTAI_API_BASE_URL` is built as empty;
- `DENTAI_PROXY_TARGET` is not used or required;
- no production CORS change is needed for frontend-to-backend requests.

The root Dockerfile builds the Vite application in a Node stage, copies only `dist/` into the final Python image at `/app/frontend-dist`, and continues to run Uvicorn as PID 1. Node and `node_modules` are not present in the runtime image.

## Local Vite development

Install, build, and start the frontend with:

```bash
npm install
npm run build
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

To test the deployed Railway backend from a local browser without changing production CORS, create `.env.local`:

```dotenv
VITE_DENTAI_API_BASE_URL=
DENTAI_PROXY_TARGET=https://dentai-production-13d1.up.railway.app
```

Keep `VITE_DENTAI_API_BASE_URL` empty. Browser requests remain same-origin to Vite at `/api`, `/health`, and `/ready`; the local Vite development server proxies them to `DENTAI_PROXY_TARGET`.

`DENTAI_PROXY_TARGET` is read only by the local Vite development server and is not included in the browser bundle. The backend origin is not a secret. Do not include credentials, tokens, database URLs, or other secrets in either variable.

When `DENTAI_PROXY_TARGET` is absent, the local proxy falls back to `http://localhost:8000`.

## First product test

1. Confirm the DENTAI web service and AI worker are running.
2. Open the frontend and confirm **Health: healthy** and **Ready: ready**.
3. Sign in with the registered clinic slug, username or email, and password.
4. Confirm the signed-in user, role, clinic ID, and branch scope.
5. Choose an accessible patient.
6. Drag in or choose a JPEG, PNG, WebP, or DICOM X-ray and upload it.
7. Select the uploaded X-ray and click **Run DENTAI V5 Analysis**.
8. Watch the real analysis progress from **Queued** to **Processing**, then **Completed** or **Failed**. The UI polls the existing patient profile about every two seconds and stops after five minutes.
9. Inspect the Product View and expandable Raw JSON result.
10. If signed in as a Doctor, explicitly confirm or reject each pending finding and submit the clinician review decisions.

The interface never auto-confirms a finding. Confidence is displayed as the exact numeric value returned by the backend, without rescaling.

> AI-assisted clinical decision support. Findings require clinician review.

## Backend prerequisites

The target environment needs:

- a registered clinic;
- an initialized clinic database/schema;
- a usable active user account;
- branch and patient permissions for that user;
- an accessible patient record;
- a Doctor role for X-ray analysis and finding review;
- configured object storage for uploads;
- the asynchronous AI worker running;
- the frozen DENTAI V5 runtime artifacts and production configuration available to that worker.

## Privacy and security

Authentication tokens are held only in `sessionStorage` and are removed on logout. Passwords, tokens, patient records, and X-ray bytes are never logged. Medical records and image bytes are kept only in React/browser memory for the active page; they are not stored in `localStorage`. The project contains no analytics, telemetry, external fonts, or third-party upload integration.
