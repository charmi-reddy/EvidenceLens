# EvidenceLens backend (Phase 1)

## Setup

Python 3.13 was used in this workspace. From `backend/`:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

To run the local test suite, install `requirements-dev.txt` instead.

Set these **in the backend process environment only**:

```bash
export GEMINI_API_KEY='your-key'
export GEMINI_MODEL='exact-model-name-from-the-Google-API-model-list'
export PORT=5000 # optional
```

The model is intentionally not defaulted or guessed. First run the live API check below; it verifies the configured model appears in the key's model listing and advertises `generateContent`, then sends real image inputs. Listing capability metadata alone does not prove image support, so successful real image requests are also required.

## Run and check

```bash
python app.py
# another terminal
curl -sS http://localhost:5000/api/health
python verify_gemini.py
```

The verification script creates a simple PNG test image locally and calls the configured Gemini model for supported (red circle), contradicted (blue square), and not visually determinable (Hyderabad location) claims. It prints actual model outcomes and returns nonzero if the expected classes were not returned. It requires valid live API credentials and model access; it does not fake responses.

## API

`GET /api/health` returns service status and whether both required Gemini environment values are configured. It does not call Gemini.

`POST /api/analyze` accepts `multipart/form-data`:

- `image`: JPEG, PNG, or WEBP image; max 10 MiB
- `caption`: non-empty text; max 5,000 characters

Success JSON:

```json
{
  "overall_status": "supported|contradicted|insufficient_evidence",
  "claims": [
    {
      "text": "A red ball is visible.",
      "status": "supported|contradicted|insufficient_evidence",
      "evidence": "A red circular object is visible near the center.",
      "explanation": "The visible object matches the claim.",
      "confidence": "low|medium|high"
    }
  ],
  "limitations": ["The image cannot establish when it was captured."]
}
```

Errors use `{"error":{"message":"..."}}`. Gemini errors are mapped to safe JSON responses (502 for generic/provider-format errors, 429 for rate limit/quota, 503 for unavailable/auth configuration). Provider error details, API keys, and model response text are not included in application logs or error responses.

## Production entry point

The WSGI application object is `app` in `app.py`. Do not use the `if __name__ == "__main__"` Flask development server for a public deployment. Install `requirements.txt` and run Gunicorn from this directory:

```bash
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 70 app:app
```

Set `GEMINI_API_KEY` and `GEMINI_MODEL` in the backend host's secret/environment settings; the host supplies `PORT` (the local fallback is 5000). The 70-second worker timeout is longer than the Gemini client's 60-second timeout.
