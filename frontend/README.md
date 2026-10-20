# EvidenceLens frontend (Phase 2)

React + Vite + Tailwind CSS frontend for the Flask API in `../backend`.

## Run locally

1. Start the backend from `../backend` using its setup instructions. Its Flask app defaults to port 5000; this was verified against the actual backend implementation and running health endpoint.
2. In `frontend/`:

```bash
npm install
cp .env.example .env.development
npm run dev
```

Vite serves the UI on port 5173 and proxies `/api/*` to `BACKEND_URL`. The browser sends same-origin `/api/analyze` requests; it never reads or receives the Gemini key. Change `BACKEND_URL` if Flask is listening elsewhere. `VITE_API_BASE_URL` sets the API path/base for the browser (default `/api`).

### Production frontend/backend connection

The Vite development proxy is not part of the production static build. For separately hosted services, build with `VITE_API_BASE_URL=https://<backend-host>/api` (the API base, without `/analyze`). The Flask backend currently has no CORS middleware. Either configure the frontend host to proxy `/api/*` to Flask, or allow the exact deployed frontend origin in backend CORS for `GET`, `POST`, and `OPTIONS` and the `Content-Type` request header. Do not use `*` when credentials or private data are involved. `BACKEND_URL` is for the Vite dev proxy only and is not exposed to the production browser bundle.

## Tests

```bash
npm run build
npx playwright install chromium    # one-time browser setup
npm run test:e2e
```

The first Playwright test uploads a small local test image through the UI and calls the live backend/Gemini API; it checks the actual response and rendered evidence. The second test aborts the request at the browser network layer to check the visible unreachable-API error and retry affordance. The tests do not stub successful analysis data.

## Limits

The app accepts JPEG, PNG, and WEBP up to 10 MiB, with captions up to 5,000 characters, matching the backend's current validation. Image results are displayed as returned by the backend after a small browser-side schema sanity check. Insufficient evidence remains distinct from contradiction, and the UI explicitly notes that visual consistency does not prove authenticity.
