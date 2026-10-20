# EvidenceLens

EvidenceLens is a web app for comparing factual claims in a caption with visible content in an image. It sends an uploaded image and caption to a configured Gemini model, then displays structured, per-claim judgments with visual evidence, explanations, confidence, limitations, and an overall status.

> **Important limitation:** image-caption consistency is not proof that an image is authentic. An image alone ordinarily cannot establish when or where it was captured, whether it is authentic, or what happened outside the frame. Claims that cannot be assessed from visible evidence should remain `insufficient_evidence`, not be treated as contradicted.

## What it does

- Accepts JPEG, PNG, or WEBP images up to 10 MiB and captions up to 5,000 characters.
- Extracts individual factual claims and classifies each as `supported`, `contradicted`, or `insufficient_evidence`.
- Returns an overall status, observable evidence, an explanation, a qualitative confidence level, and task limitations.
- Keeps the Gemini API key on the backend; it is not needed in frontend code.
- Handles input validation, unavailable service responses, quota/rate-limit errors, and malformed model output.

## Architecture

- `frontend/` — React and Vite interface; Vite proxies `/api/*` to Flask during local development.
- `backend/` — Flask API, Pydantic response schema, and Gemini integration.
- `fixtures/` — deterministic example response data used by tests and UI development; not live model output.
- `evaluation/` — synthetic cases, locally generated images, scoring code, and an explicitly limited historical live smoke report.

The development proxy is only for local development. It is not included in the production static frontend build.

## Requirements

- Python 3.10 or newer (the project has been tested with Python 3.13).
- Node.js and npm.
- A Gemini API key and an accessible Gemini model for live analysis. Supply the exact model name via `GEMINI_MODEL`; the application does not guess a default.

## Run locally

Open two terminals from the project root.

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set these in this shell only. Do not commit credentials or put them in frontend files.
export GEMINI_API_KEY='your-key'
export GEMINI_MODEL='your-model-name'
export PORT=5000  # optional; defaults to 5000

python app.py
```

The backend listens on `http://localhost:5000`. Check that it is running and that both required environment variables are configured:

```bash
curl -sS http://localhost:5000/api/health
```

This health check does not make a Gemini request. It reports service status and whether the required model settings are present; it does not verify that the key or model can successfully analyze an image.

### 2. Frontend

```bash
cd frontend
npm ci
cp .env.example .env.development
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). The browser sends same-origin `/api` requests to Vite, which forwards them to `BACKEND_URL` (default `http://127.0.0.1:5000`). `VITE_API_BASE_URL` defaults to `/api`. The Gemini key must never be put in a `VITE_*` variable or any frontend file.

## API

### `GET /api/health`

Returns service status and whether `GEMINI_API_KEY` and `GEMINI_MODEL` are configured. It does not contact Gemini.

### `POST /api/analyze`

Send `multipart/form-data` with:

- `image`: JPEG, PNG, or WEBP, maximum 10 MiB.
- `caption`: non-empty text, maximum 5,000 characters.

A successful response has this shape:

```json
{
  "overall_status": "supported",
  "claims": [
    {
      "text": "A red circle is visible.",
      "status": "supported",
      "evidence": "A red circular shape is visible in the image.",
      "explanation": "The visible shape matches the claim.",
      "confidence": "high"
    }
  ],
  "limitations": [
    "The analysis is limited to the visual content presented in the image."
  ]
}
```

Allowed verdicts are `supported`, `contradicted`, and `insufficient_evidence`; confidence is `low`, `medium`, or `high`. The overall verdict summarizes the individual claims. Error responses use `{"error":{"message":"..."}}`. Input errors use appropriate 4xx statuses; Gemini quota/rate-limit errors are surfaced as 429, while unavailable or configuration/access errors are returned as service errors. Provider details and secrets are not included in error responses.

## Tests and build

### Backend and evaluation tests

From the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -r ../evaluation/requirements.txt
python -m pytest -q test_app.py test_fixtures.py ../evaluation/test_evaluate.py
```

The backend tests use local test doubles; they do not require a live Gemini call.

### Frontend

From `frontend/`:

```bash
npm ci
npm run build
npx playwright install chromium  # one-time browser setup, if needed
```

Run all browser tests with:

```bash
npm run test:e2e
```

The browser suite includes a real-API integration test, which sends an image to the configured backend/Gemini model and therefore requires valid credentials, model access, and available quota. For offline browser coverage that excludes that live test:

```bash
npm run test:e2e -- --grep-invert 'real API result'
```

The other browser checks use local responses or network interception for deterministic UI/error scenarios; those results are test fixtures, not model predictions.

## Evaluation data and interpretation

The evaluation set contains 9 synthetic image-caption cases, 15 manually assigned claim labels, and 2 simple locally generated images. It is useful for reproducible local checks, not as an external benchmark or representative sample of real photographs. Labels have not been independently adjudicated.

The historical live smoke data contains only two successful observed claims (one `supported`, one `contradicted`) and one failed HTTP 429 request. Per-class scores based on one example are exploratory only; `insufficient_evidence` is unmeasured. These numbers are **not** a general model-accuracy estimate. Test fixtures are never scored as model output. See [`evaluation/README.md`](evaluation/README.md) for provenance, scoring details, and limitations.

To regenerate the local synthetic images and report, install `evaluation/requirements.txt`, then run from the project root:

```bash
python evaluation/generate_images.py
python evaluation/evaluate.py
```

The evaluation script is local and makes no network requests.

## Production notes

- Set `GEMINI_API_KEY` and `GEMINI_MODEL` in the backend host's secret/environment settings. Never expose the key in the browser bundle, frontend configuration, logs, or repository.
- Run Flask behind a production WSGI server such as Gunicorn; do not expose the Flask development server publicly. The backend README documents a Gunicorn command.
- Build the frontend with `npm run build` and publish `frontend/dist/`.
- For separately hosted frontend and backend, the Vite proxy is unavailable in production. Configure a same-origin `/api` reverse proxy, or implement narrowly scoped CORS for the deployed frontend origin. The current Flask app does not enable CORS middleware by itself.
- Configure the frontend API base at build time if the frontend calls a separate API origin; `BACKEND_URL` only configures the Vite development proxy.
- Local `.env*` files are ignored by the backend and frontend `.gitignore` files, with `.env.example` templates allowed. Review the Git ignore/status output before pushing any repository.

## More details

- [Backend setup, model check, API, and Gunicorn](backend/README.md)
- [Frontend setup and production connection](frontend/README.md)
- [Evaluation methodology and limitations](evaluation/README.md)
