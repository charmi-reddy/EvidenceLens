import json
import os
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from schemas import AnalysisResult


class GeminiNotConfigured(Exception):
    pass


class GeminiServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


# Use the GenAI API's supported Schema shape rather than passing a Python
# Pydantic class (which the installed SDK cannot serialize as response_schema).
MODEL_OUTPUT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "overall_status": {
            "type": "STRING",
            "enum": ["supported", "contradicted", "insufficient_evidence"],
        },
        "claims": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "text": {"type": "STRING"},
                    "status": {
                        "type": "STRING",
                        "enum": ["supported", "contradicted", "insufficient_evidence"],
                    },
                    "evidence": {"type": "STRING"},
                    "explanation": {"type": "STRING"},
                    "confidence": {"type": "STRING", "enum": ["low", "medium", "high"]},
                },
                "required": ["text", "status", "evidence", "explanation", "confidence"],
            },
        },
        "limitations": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["overall_status", "claims", "limitations"],
}

SYSTEM_INSTRUCTIONS = """You are EvidenceLens, a cautious text-image consistency analyst.
Extract each distinct, independently checkable factual assertion from the caption as an atomic claim, preserving its meaning. Do not split a single relation into unnatural fragments. Include visual, object, action, color, count, location, date/time, and provenance assertions when present. Analyze every extracted claim against the supplied image.
Use supported only when visible evidence supports it; contradicted only when clear visible evidence conflicts; otherwise use insufficient_evidence. An image ordinarily cannot establish its capture location, timestamp, authenticity, or events outside the frame. Do not infer these. A caption containing no factual claims is not analyzable and must produce a valid error-free response with a single claim saying "No verifiable factual claim was identified" and status insufficient_evidence.
Evidence must be specific observable image content, not invented details. If there is no relevant visible evidence, say so. Explain the reasoning concisely. Confidence is qualitative low/medium/high and reflects certainty in this visual judgment, not authenticity. Include limitations relevant to the image and task. Consistency never proves authenticity.
Return only JSON matching the requested schema, with exactly these top-level keys: overall_status, claims, limitations. Each claim has exactly: text, status, evidence, explanation, confidence. Status values: supported, contradicted, insufficient_evidence. Confidence values: low, medium, high. Overall status summarizes the set: contradicted if any claim is contradicted; otherwise insufficient_evidence if any is insufficient; otherwise supported."""


class GeminiAnalyzer:
    def __init__(self) -> None:
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.model = os.environ.get("GEMINI_MODEL", "").strip()
        if not self.api_key or not self.model:
            raise GeminiNotConfigured("GEMINI_API_KEY and GEMINI_MODEL must be set")
        self.client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=60_000),
        )

    def analyze(self, image_bytes: bytes, mime_type: str, caption: str) -> AnalysisResult:
        prompt = (
            f"Analyze the image and caption below. Extract atomic factual claims and assess each.\n"
            f"CAPTION:\n{caption}\n\nReturn JSON only."
        )
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTIONS,
                    response_mime_type="application/json",
                    response_schema=MODEL_OUTPUT_SCHEMA,
                    temperature=0.1,
                ),
            )
            raw = response.text
            if not raw:
                raise GeminiServiceError("The model returned an empty response")
            parsed: Any = json.loads(raw)
            result = AnalysisResult.model_validate(parsed)
            _check_overall_status(result)
            return result
        except GeminiServiceError:
            raise
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            # Do not return or log model content; malformed output is safely rejected.
            raise GeminiServiceError("The model returned an invalid structured response") from exc
        except Exception as exc:
            # SDK exception messages can contain request metadata; keep them out of responses/logs.
            code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            if code == 429:
                raise GeminiServiceError(
                    "Gemini rate limit or quota exceeded. Check API quota/billing and retry later.", 429
                ) from exc
            if code in (401, 403):
                raise GeminiServiceError(
                    "Gemini rejected the API key or model access. Check credentials and model permissions.", 503
                ) from exc
            if code == 503:
                raise GeminiServiceError("Gemini is temporarily unavailable. Retry shortly.", 503) from exc
            raise GeminiServiceError("The Gemini request failed", 502) from exc

    def verify_model(self) -> dict[str, Any]:
        """Check the configured name is available and advertises generateContent support."""
        try:
            models = self.client.models.list()
            for model in models:
                name = (getattr(model, "name", "") or "").removeprefix("models/")
                if name == self.model.removeprefix("models/"):
                    actions = getattr(model, "supported_actions", None) or []
                    actions = [str(action).lower() for action in actions]
                    if not any("generatecontent" in action for action in actions):
                        return {"available": True, "generate_content": False}
                    return {"available": True, "generate_content": True}
            return {"available": False, "generate_content": False}
        except Exception as exc:
            raise GeminiServiceError("Could not verify the configured Gemini model") from exc


def _check_overall_status(result: AnalysisResult) -> None:
    statuses = {claim.status.value for claim in result.claims}
    if "contradicted" in statuses:
        expected = "contradicted"
    elif "insufficient_evidence" in statuses:
        expected = "insufficient_evidence"
    else:
        expected = "supported"
    if result.overall_status.value != expected:
        raise GeminiServiceError("The model returned inconsistent overall and claim statuses")
