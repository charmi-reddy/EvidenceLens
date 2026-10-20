import io
import os

from flask import Flask, jsonify, request
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError

from gemini_service import GeminiAnalyzer, GeminiNotConfigured, GeminiServiceError

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_CAPTION_CHARS = 5000
ALLOWED_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def create_app(analyzer=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_BYTES + 64 * 1024
    app.config["GEMINI_ANALYZER"] = analyzer

    def get_analyzer():
        current = app.config.get("GEMINI_ANALYZER")
        if current is None:
            current = GeminiAnalyzer()
            app.config["GEMINI_ANALYZER"] = current
        return current

    @app.get("/api/health")
    def health():
        ready = bool(os.environ.get("GEMINI_API_KEY", "").strip() and os.environ.get("GEMINI_MODEL", "").strip())
        return jsonify({"status": "ok", "gemini_configured": ready}), 200

    @app.post("/api/analyze")
    def analyze():
        if not request.content_type or not request.content_type.lower().startswith("multipart/form-data"):
            return error("Expected multipart/form-data with 'image' and 'caption' fields", 415)
        upload = request.files.get("image")
        caption = request.form.get("caption", "").strip()
        if upload is None:
            return error("Missing required 'image' file field", 400)
        if not caption:
            return error("Caption must not be empty", 400)
        if len(caption) > MAX_CAPTION_CHARS:
            return error(f"Caption must be at most {MAX_CAPTION_CHARS} characters", 413)
        image_bytes = upload.stream.read(MAX_IMAGE_BYTES + 1)
        if not image_bytes:
            return error("Image file is empty", 400)
        if len(image_bytes) > MAX_IMAGE_BYTES:
            return error("Image exceeds the 10 MiB size limit", 413)
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                image_format = image.format
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            return error("Image is invalid or cannot be decoded", 400)
        mime_type = ALLOWED_FORMATS.get(image_format)
        if not mime_type:
            return error("Unsupported image type. Use JPEG, PNG, or WEBP", 415)

        try:
            result = get_analyzer().analyze(image_bytes, mime_type, caption)
            return jsonify(result.model_dump(mode="json")), 200
        except GeminiNotConfigured:
            return error("Gemini is not configured. Set GEMINI_API_KEY and GEMINI_MODEL on the backend.", 503)
        except GeminiServiceError as exc:
            return error(str(exc), exc.status_code)
        except Exception:
            # Keep unexpected errors and secrets out of the client response.
            app.logger.error("Unexpected analysis error (details suppressed)")
            return error("An unexpected server error occurred", 500)

    @app.errorhandler(413)
    def request_too_large(_exc):
        return error("Request exceeds the allowed size", 413)

    return app


def error(message: str, status: int):
    return jsonify({"error": {"message": message}}), status


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
