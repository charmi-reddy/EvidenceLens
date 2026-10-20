import io

from PIL import Image

from app import create_app


class FakeAnalyzer:
    def analyze(self, image_bytes, mime_type, caption):
        from schemas import AnalysisResult
        return AnalysisResult.model_validate({
            "overall_status": "supported",
            "claims": [{"text": caption, "status": "supported", "evidence": "A visible red circle.",
                        "explanation": "The image shows a red circular object.", "confidence": "high"}],
            "limitations": ["The image cannot establish authenticity."],
        })


def png_bytes():
    image = Image.new("RGB", (4, 4), "white")
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def test_health():
    client = create_app(FakeAnalyzer()).test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_valid_analyze_response_schema():
    client = create_app(FakeAnalyzer()).test_client()
    response = client.post("/api/analyze", data={"caption": "A red circle" ,
        "image": (io.BytesIO(png_bytes()), "image.png")}, content_type="multipart/form-data")
    assert response.status_code == 200
    assert set(response.json) == {"overall_status", "claims", "limitations"}
    assert response.json["claims"][0]["status"] == "supported"


def test_missing_image_is_rejected():
    client = create_app(FakeAnalyzer()).test_client()
    response = client.post("/api/analyze", data={"caption": "A claim"}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "error" in response.json


def test_wrong_content_type_is_rejected():
    client = create_app(FakeAnalyzer()).test_client()
    response = client.post("/api/analyze", json={"caption": "A claim"})
    assert response.status_code == 415
    assert "error" in response.json


def test_missing_gemini_configuration_returns_503(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    client = create_app().test_client()
    response = client.post("/api/analyze", data={"caption": "A claim",
        "image": (io.BytesIO(png_bytes()), "image.png")}, content_type="multipart/form-data")
    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json["error"]["message"]


def test_empty_caption_is_rejected_before_analysis():
    client = create_app(FakeAnalyzer()).test_client()
    response = client.post("/api/analyze", data={"caption": "   ",
        "image": (io.BytesIO(png_bytes()), "image.png")}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "Caption must not be empty" in response.json["error"]["message"]


def test_gemini_failure_becomes_safe_json_error():
    from gemini_service import GeminiServiceError

    class BrokenAnalyzer:
        def analyze(self, image_bytes, mime_type, caption):
            raise GeminiServiceError("Gemini is temporarily unavailable. Retry shortly.", 503)

    client = create_app(BrokenAnalyzer()).test_client()
    response = client.post("/api/analyze", data={"caption": "A claim",
        "image": (io.BytesIO(png_bytes()), "image.png")}, content_type="multipart/form-data")
    assert response.status_code == 503
    assert response.json == {"error": {"message": "Gemini is temporarily unavailable. Retry shortly."}}


def test_gemini_output_schema_serializes_with_installed_sdk():
    from google.genai import types
    from gemini_service import MODEL_OUTPUT_SCHEMA

    config = types.GenerateContentConfig(
        response_mime_type="application/json", response_schema=MODEL_OUTPUT_SCHEMA
    )
    serialized = config.to_json_dict()
    assert serialized["response_schema"]["type"] == "OBJECT"
    assert "claims" in serialized["response_schema"]["properties"]


def test_unsupported_file_is_rejected():
    client = create_app(FakeAnalyzer()).test_client()
    response = client.post("/api/analyze", data={"caption": "A claim",
        "image": (io.BytesIO(b"not an image"), "image.txt")}, content_type="multipart/form-data")
    assert response.status_code == 400
