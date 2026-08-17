# DENTAI Internal Product Test Frontend

An isolated React + TypeScript + Vite interface for the first real end-to-end DENTAI product test. It uses the existing backend contracts and does not change backend behavior.

## Start

```bash
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`).

Create a production build with:

```bash
npm run build
```

## API configuration

Copy `.env.example` to `.env.local`. For the preferred Railway-backed local test, use:

```dotenv
VITE_DENTAI_API_BASE_URL=
DENTAI_PROXY_TARGET=https://your-dentai-production-domain.example
```

Keep `VITE_DENTAI_API_BASE_URL` empty. Browser requests then remain same-origin to Vite at `/api`, `/health`, and `/ready`; the Vite development server proxies them to `DENTAI_PROXY_TARGET`. This tests a remote Railway backend from a local browser without adding localhost to production CORS.

`DENTAI_PROXY_TARGET` is read only by the Vite development server and is not included in the browser bundle. The backend origin is not a secret. Do not include credentials, tokens, database URLs, or other secrets in either variable.

When `DENTAI_PROXY_TARGET` is absent, the proxy falls back to `http://localhost:8000`.

A direct browser-to-backend setup is also available by setting `VITE_DENTAI_API_BASE_URL` to the backend origin, without `/api/v1`, but that requires the backend CORS policy to allow the frontend origin.

## First product test

1. Confirm the remote backend and AI worker are running.
2. Start this frontend and confirm **Health: healthy** and **Ready: ready**.
3. Sign in with the registered clinic slug, username or email, and password.
4. Confirm the signed-in user, role, clinic ID, and branch scope.
5. Choose an accessible patient.
6. Drag in or choose a JPEG, PNG, WebP, or DICOM X-ray and upload it.
7. Select the uploaded X-ray and click **Run DENTAI V5 Analysis**.
8. Watch the real analysis progress from **Queued** to **Processing**, then **Completed** or **Failed**. The UI polls the existing patient profile about every two seconds and stops after five minutes.
9. Inspect the Product View and expandable Raw JSON result.
10. If signed in as a Doctor, explicitly confirm or reject each pending finding and submit the clinician review decisions.

The interface never auto-confirms a finding. Confidence is displayed as the exact numeric value returned by the backend, without rescaling. It displays the required warning:

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

The proxy target must expose `/health`, `/ready`, and the existing `/api/v1` routes.

## Privacy and security

Authentication tokens are held only in `sessionStorage` and are removed on logout. Passwords, tokens, patient records, and X-ray bytes are never logged. Medical records and image bytes are kept only in React/browser memory for the active page; they are not stored in `localStorage`. The project contains no analytics, telemetry, external fonts, or third-party upload integration.
