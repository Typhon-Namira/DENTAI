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

Copy `.env.example` to `.env.local` and set:

```dotenv
VITE_DENTAI_API_BASE_URL=https://your-dentai-api.example
```

Use the backend origin only, without `/api/v1`. An empty value makes requests same-origin. During local development, the included Vite proxy sends `/api`, `/health`, and `/ready` to `http://localhost:8000`, avoiding browser CORS restrictions when the backend is running locally.

For a remote API, its CORS configuration must permit the frontend origin. Do not put credentials or secrets in Vite environment variables; Vite variables are public browser configuration.

## First product test

1. Start the backend and AI worker.
2. Open the frontend and confirm **Health: healthy** and **Ready: ready**.
3. Sign in with the registered clinic slug, username or email, and password.
4. Confirm the signed-in user, role, clinic ID, and branch scope.
5. Choose an accessible patient.
6. Drag in or choose a JPEG, PNG, WebP, or DICOM X-ray and upload it.
7. Select the uploaded X-ray and click **Run DENTAI V5 Analysis**.
8. Watch the real analysis progress from **Queued** to **Processing**, then **Completed** or **Failed**. The UI polls the existing patient profile about every two seconds and stops after five minutes.
9. Inspect the Product View and expandable Raw JSON result.
10. If signed in as a Doctor, explicitly confirm or reject each pending finding and submit the clinician review.

The interface never auto-confirms a finding. It displays the required warning:

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

The API base must expose `/health`, `/ready`, and the existing `/api/v1` routes.

## Privacy and security

Authentication tokens are held only in `sessionStorage` and are removed on logout. Passwords, tokens, patient records, and X-ray bytes are never logged. Medical records and image bytes are kept only in React/browser memory for the active page; they are not stored in `localStorage`. The project contains no analytics, telemetry, external fonts, or third-party upload integration.
